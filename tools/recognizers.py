import cadquery as cq
from typing import Any, Dict

def recognize_shape(obj: Any) -> Dict:
    try:
        val = obj.val() if hasattr(obj, "val") else obj
        bb = val.BoundingBox()
        return {
            "bbox": [bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax],
            "faces": len(val.Faces()) if hasattr(val, "Faces") else None,
            "edges": len(val.Edges()) if hasattr(val, "Edges") else None,
        }
    except Exception as e:
        return {"error": str(e)}