import cadquery as cq
import io, json, base64, traceback
from typing import Dict, Any

SAFE_GLOBALS = {"cq": cq, "result": None, "wp": cq.Workplane("XY"), "sk": None}

class CQEnv:
    """在受限全局变量下执行 CadQuery 代码，并返回摘要与（可选）渲染。"""
    def __init__(self):
        self.globals = dict(SAFE_GLOBALS)

    def reset(self):
        self.globals = dict(SAFE_GLOBALS)

    def run(self, code: str) -> Dict[str, Any]:
        try:
            local_ns = {}
            exec(code, self.globals, local_ns)
            # 允许用户把 result 放在 globals 或 locals
            result = local_ns.get("result") or self.globals.get("result") or self.globals.get("wp")
            summary = self._summarize(result)
            img = self._render_placeholder()
            return {"ok": True, "summary": summary, "image_b64": img, "log": "ok"}
        except Exception as e:
            return {"ok": False, "summary": {}, "image_b64": "", "log": "error", "error": str(e), "trace": traceback.format_exc()}

    def _summarize(self, obj) -> Dict[str, Any]:
        try:
            val = obj.val() if hasattr(obj, "val") else obj
            bb = val.BoundingBox()
            vol = getattr(val, "Volume", None) or getattr(val, "volume", None)
            return {
                "bbox": [bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax],
                "volume": float(vol()) if callable(vol) else None,
                "type": type(val).__name__,
            }
        except Exception:
            return {"type": str(type(obj))}

    def _render_placeholder(self) -> str:
        # 这里先返回空图像；后续可接入 OCC 视图或 trimesh。
        png = b""
        return base64.b64encode(png).decode("ascii")