"""
Error Annotation Agent — provides detailed multi-dimensional annotations
for fields classified as genuine errors, including root cause analysis.
"""

import json

from agents.base import call_agent, load_prompt

SYSTEM_PROMPT = load_prompt("annotation")


def run(raw_input: str, classification: dict, error_fields: list) -> dict | None:
    user_prompt = (
        f"原始输入: {raw_input}\n"
        f"分类结果: {json.dumps(classification, ensure_ascii=False)}\n"
        f"需要标注的错误字段: {json.dumps(error_fields, ensure_ascii=False)}"
    )
    return call_agent("annotation", SYSTEM_PROMPT, user_prompt)
