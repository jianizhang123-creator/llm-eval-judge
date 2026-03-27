"""
POST /api/analyze — Pattern Analysis + Prompt Insight pipeline (SSE stream).
Reads all accumulated errors and generates optimization suggestions.
"""

from flask import Blueprint, Response

from agents import pattern_analysis, prompt_insight
from eval_store.store import load_data, save_data
from events.stream import sse_event

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.route("/api/analyze", methods=["POST"])
def api_analyze():
    def generate():
        data = load_data()
        kb = data["knowledge_base"]
        errors = kb.get("errors", [])
        stats = kb.get("stats", {})

        if not errors:
            yield sse_event("error", {
                "message": "知识库中暂无错误记录，请先评估一些样本。"
            })
            return

        # --- Pattern Analysis Agent ---
        yield sse_event("agent_start", {"agent": "pattern_analysis"})
        pattern_result = pattern_analysis.run(errors, stats)
        if not pattern_result:
            yield sse_event("error", {"message": "Pattern analysis agent failed"})
            return
        yield sse_event("agent_done", {
            "agent": "pattern_analysis", "result": pattern_result
        })

        # --- Prompt Insight Agent ---
        yield sse_event("agent_start", {"agent": "prompt_insight"})
        insight_result = prompt_insight.run(pattern_result, stats)
        if not insight_result:
            yield sse_event("error", {"message": "Prompt insight agent failed"})
            return
        yield sse_event("agent_done", {
            "agent": "prompt_insight", "result": insight_result
        })

        # --- Persist patterns ---
        kb["patterns"] = pattern_result.get("patterns", kb.get("patterns", []))
        save_data(data)

        yield sse_event("analysis_complete", {
            "patterns": pattern_result,
            "insights": insight_result,
        })

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})
