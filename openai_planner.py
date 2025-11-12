# openai_planner.py
from __future__ import annotations
import os, json, pathlib
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

@dataclass
class StepFeedback:
    ok: bool
    summary: Dict[str, Any]
    image_b64: str
    log: str
    error: Optional[str] = None

class OpenAIPlannerChain:
    def __init__(self, system_path: str = "prompts/system_tools.md", model: str = None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.system_prompt = pathlib.Path(system_path).read_text(encoding="utf-8")

    def step(self, goal: str, feedback: Optional[StepFeedback] = None) -> Dict[str, Any]:
        msgs: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"任务：{goal}\n\n请只按指定 JSON schema 输出。"},
        ]
        if feedback is not None:
            # 将上一步执行结果回灌，以便模型修正
            fb_json = json.dumps({
                "ok": feedback.ok,
                "summary": feedback.summary,
                "has_image": bool(feedback.image_b64),
                "error": feedback.error,
                "log": feedback.log[-800:] if feedback.log else "",
            }, ensure_ascii=False)
            msgs.append({"role": "user", "content": f"上一步执行反馈：{fb_json}"})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=msgs,
            temperature=0.2,
        )
        content = resp.choices[0].message.content
        # 期望模型输出就是 JSON；兜底：尝试截取 JSON
        try:
            obj = json.loads(content)
        except Exception:
            start = content.find('{')
            end = content.rfind('}') + 1
            obj = json.loads(content[start:end])
        # 归一化字段
        plan = obj.get("plan", "")
        code = obj.get("action_code", "")
        term = bool(obj.get("terminate", False))
        return {"plan": plan, "action_code": code, "terminate": term}