# runners/text_to_cq_miniloop.py
import os, json, base64
from env.cq_env import CQEnv
from openai_planner import OpenAIPlannerChain

GOAL = os.environ.get("CQ_GOAL", "在 XY 平面画 60x40 矩形，四角 5mm 圆角，拉伸 10mm。")

if __name__ == "__main__":
    planner = OpenAIPlannerChain()
    env = CQEnv(result_root="result")

    step = planner.step(GOAL)
    print("[PLANNER]", json.dumps({k: (v if k != 'action_code' else '...code omitted...') for k,v in step.items()}, ensure_ascii=False))

    feedback = env.run(step.get("action_code", ""), save=True)
    # 控制台输出关键信息与结果目录
    run_dir = feedback.get("run_dir")
    print("[ENV FEEDBACK]", json.dumps({k: (v[:64]+"...") if k=="image_b64" and v else v for k,v in feedback.items() if k != 'summary'}, ensure_ascii=False, indent=2))
    if run_dir:
        print(f"运行产物已保存到: {run_dir}")