# env/cq_env.py
import cadquery as cq
from cadquery import exporters as exporters
import io, os, json, base64, traceback, tempfile, datetime
from typing import Dict, Any, Tuple, Optional

# —— 尝试加载三方渲染依赖（若失败将自动回退）——
try:
    import trimesh
    import numpy as np
    from trimesh.transformations import look_at
    _HAS_TRIMESH = True
except Exception:
    trimesh = None
    _HAS_TRIMESH = False

import matplotlib
matplotlib.use("Agg")  # 纯离屏
import matplotlib.pyplot as plt
from math import cos, sin, radians

SAFE_GLOBALS = {
    "cq": cq,                    # 只暴露 CadQuery 本体
    "result": None,              # 约定：最终形体放到 result
    "wp": cq.Workplane("XY"),   # 默认工作平面
    "sk": None,                  # 草图暂存
}

# ---- Compatibility shim: make Workplane.volume() available for LLM code ----
def _wp_volume(self):
    try:
        v = self.val()
        return float(v.Volume()) if hasattr(v, "Volume") else None
    except Exception:
        return None

if not hasattr(cq.Workplane, "volume"):
    try:
        cq.Workplane.volume = _wp_volume
    except Exception:
        pass
# ---------------------------------------------------------------------------

class CQEnv:
    """在受限全局变量下执行 CadQuery 代码，并进行渲染/落盘。"""
    def __init__(self, result_root: str = "result"):
        self.globals = dict(SAFE_GLOBALS)
        self.result_root = result_root
        os.makedirs(self.result_root, exist_ok=True)

    def reset(self):
        self.globals = dict(SAFE_GLOBALS)

    def _new_run_dir(self) -> str:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(self.result_root, ts)
        os.makedirs(run_dir, exist_ok=True)
        return run_dir

    def run(self, code: str, save: bool = True) -> Dict[str, Any]:
        run_dir = self._new_run_dir() if save else None
        if run_dir:
            with open(os.path.join(run_dir, "action_code.py"), "w", encoding="utf-8") as f:
                f.write(code)

        try:
            compiled = compile(code, filename="<action_code>", mode="exec")
            exec(compiled, self.globals, self.globals)
            obj = self.globals.get("result", None)
            if obj is None:
                out = {
                    "ok": False,
                    "summary": {},
                    "image_b64": "",
                    "log": "",
                    "error": "未找到 result。请在代码里将最终形体赋值给变量 `result`。",
                    "run_dir": run_dir,
                }
                if run_dir:
                    self._dump_json(os.path.join(run_dir, "summary.json"), out)
                return out

            summary = self._summarize(obj)

            if _HAS_TRIMESH:
                img_b64, img_bytes, render_mode, render_err = self._render_trimesh_image(obj)
            else:
                img_b64, img_bytes, render_mode, render_err = self._render_bbox_image(
                    summary.get("bbox")), None, "bbox", None

            out = {
                "ok": True,
                "summary": summary,
                "image_b64": img_b64,
                "log": "",
                "error": None,
                "render_mode": render_mode,  # 由内部实际结果决定
                "render_error": render_err,  # 如有回退会告诉你原因
                "run_dir": run_dir,
            }

            if run_dir:
                if img_bytes:
                    with open(os.path.join(run_dir, "render.png"), "wb") as f:
                        f.write(img_bytes)
                else:
                    # 从 base64 落盘（bbox 回退路径）
                    if img_b64:
                        with open(os.path.join(run_dir, "render.png"), "wb") as f:
                            f.write(base64.b64decode(img_b64))
                self._dump_json(os.path.join(run_dir, "summary.json"), out)
            return out

        except Exception:
            tb = traceback.format_exc(limit=6)
            out = {
                "ok": False,
                "summary": {},
                "image_b64": "",
                "log": "",
                "error": tb,
                "run_dir": run_dir,
            }
            if run_dir:
                self._dump_json(os.path.join(run_dir, "summary.json"), out)
            return out

    # —— 几何摘要 ——
    def _summarize(self, obj: Any) -> Dict[str, Any]:
        try:
            val = obj.val() if hasattr(obj, "val") else obj
            bb = val.BoundingBox()
            vol = None
            if hasattr(val, "Volume"):
                v = val.Volume()
                vol = float(v) if v is not None else None
            elif hasattr(val, "volume"):
                v = val.volume()
                vol = float(v) if v is not None else None
            faces = len(val.Faces()) if hasattr(val, "Faces") else None
            edges = len(val.Edges()) if hasattr(val, "Edges") else None
            return {
                "bbox": [bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax],
                "volume": vol,
                "faces": faces,
                "edges": edges,
                "type": type(val).__name__,
            }
        except Exception:
            return {"type": str(type(obj))}

    # —— 基于 trimesh 的真实光栅渲染 ——
    def _render_trimesh_image(self, obj: Any, size: Tuple[int, int] = (900, 700)) -> Tuple[
        str, Optional[bytes], str, Optional[str]]:
        """
        尝试用 trimesh 做真实 3D 渲染；失败则回退 bbox。
        返回: (base64, bytes_or_None, mode, error_or_None)
              mode ∈ {"trimesh", "bbox"}
        """
        try:
            val = obj.val() if hasattr(obj, "val") else obj

            # 导出 STL → 加载
            with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
                tmp_path = tmp.name
            try:
                from cadquery import exporters as exporters  # 你环境可用
                exporters.export(val, tmp_path)
                mesh = trimesh.load(tmp_path)
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            # 构建场景 + 设相机（等轴测+透视）
            import numpy as np
            from trimesh.transformations import look_at

            scene = trimesh.Scene(mesh)
            center = mesh.bounds.mean(axis=0)
            extents = float(mesh.extents.max())
            eye = center + np.array([1.7, -1.7, 1.2]) * extents
            up = np.array([0.0, 0.0, 1.0])

            cam = trimesh.scene.cameras.Camera(resolution=size, fov=(50, 35))
            scene.camera = cam
            scene.camera_transform = look_at(eye=eye, target=center, up=up)
            scene.background = [255, 255, 255, 255]

            data = scene.save_image(resolution=size, visible=True)  # bytes(PNG)
            b64 = base64.b64encode(data).decode("ascii") if data else ""
            return b64, data, "trimesh", None

        except Exception as e:
            # 回退到 bbox 线框
            try:
                summary = self._summarize(obj)
                b64 = self._render_bbox_image(summary.get("bbox"))
            except Exception:
                b64 = ""
            return b64, None, "bbox", f"{type(e).__name__}: {e}"

    # —— 基于包围盒的等轴测“简易渲染” ——
    def _render_bbox_image(self, bbox: Any, size: Tuple[int, int] = (640, 480)) -> str:
        if not bbox or len(bbox) != 6:
            return ""
        xmin, ymin, zmin, xmax, ymax, zmax = bbox
        pts = [
            (xmin, ymin, zmin), (xmax, ymin, zmin), (xmax, ymax, zmin), (xmin, ymax, zmin),
            (xmin, ymin, zmax), (xmax, ymin, zmax), (xmax, ymax, zmax), (xmin, ymax, zmax)
        ]
        ax = radians(35.264); ay = radians(45)
        def proj(p):
            x, y, z = p
            y2 = y*cos(ax) - z*sin(ax)
            x3 = x*cos(ay) - y2*sin(ay)
            y3 = x*sin(ay) + y2*cos(ay)
            return (x3, y3)
        P = list(map(proj, pts))
        edges = [(0,1),(1,2),(2,3),(3,0), (4,5),(5,6),(6,7),(7,4), (0,4),(1,5),(2,6),(3,7)]
        fig = plt.figure(figsize=(size[0]/100, size[1]/100), dpi=100)
        axp = fig.add_subplot(111)
        axp.set_aspect('equal', adjustable='box'); axp.axis('off')
        for i,j in edges:
            x1,y1 = P[i]; x2,y2 = P[j]
            axp.plot([x1,x2],[y1,y2])
        xs, ys = zip(*P)
        pad = 0.1 * max(max(xs)-min(xs), max(ys)-min(ys))
        axp.set_xlim(min(xs)-pad, max(xs)+pad); axp.set_ylim(min(ys)-pad, max(ys)+pad)
        buf = io.BytesIO(); fig.tight_layout(pad=0)
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0); plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode('ascii')

    @staticmethod
    def _dump_json(path: str, obj: Dict[str, Any]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)