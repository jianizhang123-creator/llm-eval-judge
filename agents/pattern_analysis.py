"""
Pattern Analysis Agent — identifies recurring error patterns and systemic
issues across all accumulated errors in the knowledge base.
"""

import json

from agents.base import call_agent, load_prompt

SYSTEM_PROMPT = load_prompt("pattern_analysis")


def run(errors: list, stats: dict) -> dict | None:
    user_prompt = (
        f"以下是错误知识库中的所有标注错误 ({len(errors)} 条):\n"
        f"{json.dumps(errors, ensure_ascii=False)}\n\n"
        f"当前质量统计:\n"
        f"{json.dumps(stats, ensure_ascii=False)}\n\n"
        f"请分析这些错误中的规律和系统性问题。"
    )
    return call_agent("pattern_analysis", SYSTEM_PROMPT, user_prompt)
