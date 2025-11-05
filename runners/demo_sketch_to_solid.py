import json
from env.cq_env import CQEnv

# 目标
GOAL = "生成一个60x40矩形，四角5mm圆角，拉伸10mm，并返回体积与包围盒"

# 先不用 LLM，直接模拟一条 Planner 动作代码
ACTION = r"""
# 创建带圆角的矩形并拉伸
wp = cq.Workplane("XY")
sk = cq.Sketch().rect(60, 40).vertices().fillet(5)
result = wp.placeSketch(sk).extrude(10)
"""

if __name__ == "__main__":
    env = CQEnv()
    feedback = env.run(ACTION)
    print("ENV FEEDBACK:\n", json.dumps(feedback, ensure_ascii=False, indent=2))