"""
POST /api/batch — Batch evaluation pipeline (SSE stream).
Iterates through all (or selected) samples, running Classification +
Annotation for each.
"""

import json

from flask import Blueprint, Response, request

from agents import classification, annotation
from eval_store.store import load_data, save_data
from eval_store.stats import update_stats
from events.stream import sse_event

batch_bp = Blueprint("batch", __name__)


@batch_bp.route("/api/batch", methods=["POST"])
def api_batch():
    body = request.get_json(force=True)
    requested_ids = body.get("sample_ids", [])

    def generate():
        data = load_data()
        samples = data.get("samples", [])

        if requested_ids:
            targets = [s for s in samples if s["id"] in requested_ids]
        else:
            targets = list(samples)

        total = len(targets)
        summary = {"evaluated": 0, "correct": 0, "preference": 0,
                    "error": 0, "mixed": 0, "failed": 0}

        for idx, sample in enumerate(targets, 1):
            sid = sample["id"]
            yield sse_event("batch_progress", {
                "current": idx, "total": total, "sample_id": sid
            })

            raw_input = sample.get("input", "")
            prediction = sample.get("prediction", {})
            user_correction = sample.get("user_correction")

            # --- No correction: correct ---
            if not user_correction:
                result = {
                    "sample_id": sid, "verdict": "correct",
                    "classification": None, "annotation": None,
                }
                for s in data["samples"]:
                    if s["id"] == sid:
                        s["eval_result"] = result
                        break
                update_stats(data, {"overall_verdict": "correct"})
                summary["evaluated"] += 1
                summary["correct"] += 1
                yield sse_event("sample_done", result)
                continue

            # --- Classification ---
            cls_result = classification.run(raw_input, prediction, user_correction)
            if not cls_result:
                summary["failed"] += 1
                yield sse_event("sample_done", {"sample_id": sid, "verdict": "failed"})
                continue

            # --- Annotation (if errors) ---
            ann_result = None
            error_fields = [
                m for m in cls_result.get("modifications", [])
                if m.get("type") == "error"
            ]
            if error_fields:
                ann_result = annotation.run(raw_input, cls_result, error_fields)
                if ann_result:
                    for ann in ann_result.get("annotations", []):
                        err_id = f"e{len(data['knowledge_base']['errors']) + 1:03d}"
                        data["knowledge_base"]["errors"].append({
                            "id": err_id,
                            "sample_id": sid,
                            "field": ann.get("field", ""),
                            "error_type": ann.get("error_type", "unknown"),
                            "severity": ann.get("severity", "minor"),
                            "description": ann.get("description", ""),
                            "root_cause": ann.get("root_cause", ""),
                            "input_snippet": raw_input[:60],
                            "predicted": str(prediction.get(ann.get("field", ""), "")),
                            "corrected": str(user_correction.get(ann.get("field", ""), "")),
                        })

            verdict = cls_result.get("overall_verdict", "unknown")
            result = {
                "sample_id": sid, "verdict": verdict,
                "classification": cls_result, "annotation": ann_result,
            }
            for s in data["samples"]:
                if s["id"] == sid:
                    s["eval_result"] = result
                    break

            update_stats(data, cls_result)
            summary["evaluated"] += 1
            summary[verdict] = summary.get(verdict, 0) + 1
            yield sse_event("sample_done", result)

        save_data(data)
        yield sse_event("batch_complete", summary)
        yield sse_event("dashboard_update", data["knowledge_base"]["stats"])

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})
