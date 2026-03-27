"""
Quality metrics calculator — recalculates per-field accuracy, error-type
distribution, and hallucination rate after each evaluation.
"""


def update_stats(data: dict, classification_result: dict) -> None:
    """Recalculate knowledge-base stats after an evaluation."""
    stats = data["knowledge_base"]["stats"]
    stats["total_evaluated"] = stats.get("total_evaluated", 0) + 1

    verdict = classification_result.get("overall_verdict", "correct")
    if verdict == "preference":
        stats["preference_count"] = stats.get("preference_count", 0) + 1
    elif verdict == "error":
        stats["error_count"] = stats.get("error_count", 0) + 1
    elif verdict == "mixed":
        stats["error_count"] = stats.get("error_count", 0) + 1
        stats["preference_count"] = stats.get("preference_count", 0) + 1

    # Per-field accuracy: scan all evaluated samples
    field_correct = {"amount": 0, "category": 0, "date": 0, "merchant": 0}
    field_total = {"amount": 0, "category": 0, "date": 0, "merchant": 0}

    for sample in data["samples"]:
        er = sample.get("eval_result")
        if not er:
            continue
        cr = er.get("classification")
        if not cr:
            # "correct" samples — all fields are correct
            for f in field_correct:
                field_total[f] += 1
                field_correct[f] += 1
            continue

        mods = {m["field"]: m["type"] for m in cr.get("modifications", [])}
        for f in field_correct:
            field_total[f] += 1
            if f not in mods or mods[f] != "error":
                field_correct[f] += 1

    accuracy = {}
    for f in field_correct:
        accuracy[f] = round(field_correct[f] / field_total[f], 3) if field_total[f] else 1.0
    stats["accuracy_by_field"] = accuracy

    # Error type distribution from knowledge base errors
    dist: dict[str, int] = {}
    for err in data["knowledge_base"]["errors"]:
        et = err.get("error_type", "unknown")
        dist[et] = dist.get(et, 0) + 1
    stats["error_type_distribution"] = dist

    stats["hallucination_rate"] = round(
        dist.get("hallucination", 0) / stats["total_evaluated"], 3
    ) if stats["total_evaluated"] else 0.0
