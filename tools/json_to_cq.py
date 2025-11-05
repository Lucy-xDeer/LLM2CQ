import cadquery as cq
from typing import Dict

def build_sketch_from_json(data: Dict) -> cq.Sketch:
    s = cq.Sketch()
    prims = data.get("sketch", {}).get("primitives", [])
    for p in prims:
        t = p.get("type")
        if t == "line":
            s = s.segment((p["xs"], p["ys"]), (p["xe"], p["ye"]))
        elif t == "circle":
            s = s.circle(p["r"], (p["xc"], p["yc"]))
        elif t == "arc":
            # 优先三点式：需要提供 xm,ym；若没有可退化为整圆或两段线
            xm, ym = p.get("xm"), p.get("ym")
            if xm is not None:
                s = s.arc((p["xs"], p["ys"]), (xm, ym), (p["xe"], p["ye"]))
    # 约束（最小集合示例）
    cons = data.get("sketch", {}).get("constraints", [])
    if cons:
        c = s.constraints()
        for item in cons:
            if item["type"] == "horizontal":
                c = c.horizontal()
            elif item["type"] == "vertical":
                c = c.vertical()
        s = c.finalize()
    return s

def extrude_sketch(sk: cq.Sketch, dist: float) -> cq.Workplane:
    return cq.Workplane("XY").placeSketch(sk).extrude(dist)