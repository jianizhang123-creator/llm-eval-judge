"""
Prompt Insight Agent — generates specific, actionable prompt optimization
suggestions based on error patterns and quality metrics.
"""

import json

from agents.base import call_agent, load_prompt

SYSTEM_PROMPT = load_prompt("prompt_insight")


def run(pattern_result: dict, stats: dict) -> dict | None:
    user_prompt = (
        f"错误模式分析结果:\n"
        f"{json.dumps(pattern_result, ensure_ascii=False)}\n\n"
        f"当前质量统计:\n"
        f"{json.dumps(stats, ensure_ascii=False)}\n\n"
        f"已知错误类型分布:\n"
        f"{json.dumps(stats.get('error_type_distribution', {}), ensure_ascii=False)}\n\n"
        f"请给出具体的 prompt 优化建议。"
    )
    return call_agent("prompt_insight", SYSTEM_PROMPT, user_prompt)
