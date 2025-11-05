from __future__ import annotations
import os, json
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

class OpenAIPlanner:
    """
    VLM/LLM 驱动的最小 Planner：
    - 输入：任务指令 + 工具文档 + 上一步反馈
    - 输出：{plan, action_code, terminate}
    """
    def __init__(self,
                 model: str | None = None,
                 system_path: str = os.path.join(os.path.dirname(__file__), "..", "prompts", "system_tools.md")):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        with open(system_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
        self.history: List[Dict[str, Any]] = []

    def _compose_messages(self, goal: str, last_feedback: Optional[StepFeedback]) -> List[Dict[str, str]]:
        msgs = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"任务：{goal}"}
        ]
        if last_feedback is not None:
            fb = {
                "ok": last_feedback.ok,
                "summary": last_feedback.summary,
                "has_image": bool(last_feedback.image_b64),
                "log": last_feedback.log,
                "error": last_feedback.error,
            }
            msgs.append({"role": "user", "content": "上一步反馈：" + json.dumps(fb, ensure_ascii=False)})
        return msgs

    def step(self, goal: str, last_feedback: Optional[StepFeedback]) -> Dict[str, Any]:
        msgs = self._compose_messages(goal, last_feedback)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=msgs,
            temperature=0.2,
        )
        content = resp.choices[0].message.content
        # 期望模型输出就是 JSON
        try:
            obj = json.loads(content)
        except Exception:
            # 兜底：尝试截取 JSON
            start = content.find('{')
            end = content.rfind('}') + 1
            obj = json.loads(content[start:end])
        return obj