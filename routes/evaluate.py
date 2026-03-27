"""
POST /api/evaluate — Single-sample evaluation pipeline (SSE stream).
Runs Classification Agent, then conditionally Annotation Agent for errors.
"""

import json

from flask import Blueprint, Response, request

from agents import classification, annotation
from eval_store.store import load_data, save_data
from eval_store.stats import update_stats
from events.stream import sse_event

evaluate_bp = Blueprint("evaluate", __name__)


@evaluate_bp.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    body = request.get_json(force=True)
    sample_id = body.get("sample_id")
    raw_input = body.get("input", "")
    prediction = body.get("prediction", {})
    user_correction = body.get("user_correction")

    def generate():
        data = load_data()

        # --- No correction: mark as correct ---
        if not user_correction:
            result = {
                "sample_id": sample_id,
                "verdict": "correct",
                "classification": None,
                "annotation": None,
            }
            for s in data["samples"]:
                if s["id"] == sample_id:
                    s["eval_result"] = result
                    break
            update_stats(data, {"overall_verdict": "correct"})
            save_data(data)
            yield sse_event("eval_complete", result)
            yield sse_event("dashboard_update", data["knowledge_base"]["stats"])
            return

        # --- Classification Agent ---
        yield sse_event("agent_start", {"agent": "classification"})
        cls_result = classification.run(raw_input, prediction, user_correction)
        if not cls_result:
            yield sse_event("error", {"message": "Classification agent failed"})
            return
        yield sse_event("agent_done", {"agent": "classification", "result": cls_result})

        # --- Annotation Agent (if errors exist) ---
        ann_result = None
        error_fields = [
            m for m in cls_result.get("modifications", [])
            if m.get("type") == "error"
        ]
        if error_fields:
            yield sse_event("agent_start", {"agent": "annotation"})
            ann_result = annotation.run(raw_input, cls_result, error_fields)
            if ann_result:
                yield sse_event("agent_done", {"agent": "annotation", "result": ann_result})
                # Persist errors into knowledge base
                for ann in ann_result.get("annotations", []):
                    err_id = f"e{len(data['knowledge_base']['errors']) + 1:03d}"
                    data["knowledge_base"]["errors"].append({
                        "id": err_id,
                        "sample_id": sample_id,
                        "field": ann.get("field", ""),
                        "error_type": ann.get("error_type", "unknown"),
                        "severity": ann.get("severity", "minor"),
                        "description": ann.get("description", ""),
                        "root_cause": ann.get("root_cause", ""),
                        "input_snippet": raw_input[:60],
                        "predicted": str(prediction.get(ann.get("field", ""), "")),
                        "corrected": str(user_correction.get(ann.get("field", ""), "")),
                    })

        # --- Persist result ---
        result = {
            "sample_id": sample_id,
            "verdict": cls_result.get("overall_verdict", "unknown"),
            "classification": cls_result,
            "annotation": ann_result,
        }
        for s in data["samples"]:
            if s["id"] == sample_id:
                s["eval_result"] = result
                break

        update_stats(data, cls_result)
        save_data(data)

        yield sse_event("eval_complete", result)
        yield sse_event("dashboard_update", data["knowledge_base"]["stats"])

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})
