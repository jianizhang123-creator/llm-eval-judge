"""
Classification Agent — determines whether each user modification is a
personal preference, a genuine model error, or ambiguous.
"""

import json

from agents.base import call_agent, load_prompt

SYSTEM_PROMPT = load_prompt("classification")


def run(raw_input: str, prediction: dict, user_correction: dict) -> dict | None:
    user_prompt = (
        f"原始输入: {raw_input}\n"
        f"模型预测: {json.dumps(prediction, ensure_ascii=False)}\n"
        f"用户修改: {json.dumps(user_correction, ensure_ascii=False)}"
    )
    return call_agent("classification", SYSTEM_PROMPT, user_prompt)
