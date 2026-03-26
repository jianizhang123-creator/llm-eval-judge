"""
LLM Eval Judge - Flask Backend
Uses Claude as LLM-as-a-Judge to evaluate model output quality
in an accounting/bill parsing context.
"""

import json
import time
import re
import traceback
from pathlib import Path

from flask import Flask, request, Response, send_from_directory
from anthropic import Anthropic

# ---------------------------------------------------------------------------
# App & client
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder=".", static_url_path="")
client = Anthropic()

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2048
DATA_FILE = Path(__file__).parent / "eval_data.json"

# ---------------------------------------------------------------------------
# Agent system prompts (module-level constants)
# ---------------------------------------------------------------------------

CLASSIFICATION_SYSTEM_PROMPT = """You are an AI output quality judge for a Chinese accounting / bill-parsing application.

Given three pieces of information:
1. **原始输入 (input)** — the raw text a user typed to record a bill
2. **模型预测 (prediction)** — the structured fields the model produced
3. **用户修改 (user_correction)** — the fields the user changed

For EACH modified field, determine whether the change is:
- **"preference"** — the user simply prefers a different label/value, but the model's answer was also acceptable (e.g. "餐饮" vs "咖啡" for a Starbucks purchase)
- **"error"** — the model made a genuine factual or logical mistake (e.g. wrong amount, wrong date, hallucinated merchant)
- **"ambiguous"** — not clearly one or the other

Consider Chinese accounting conventions and common bill scenarios such as:
分期付款 (installment payments), 团购 (group buying), 转账 (transfers),
花呗/白条 (credit services), 预约/预订 (reservations).

Return ONLY valid JSON — no markdown fences, no extra text.

Output format:
{
  "modifications": [
    {
      "field": "category|amount|date|merchant",
      "original_value": "model's prediction for this field",
      "corrected_value": "user's correction",
      "type": "preference|error|ambiguous",
      "confidence": 0.0-1.0,
      "reasoning": "brief explanation in Chinese"
    }
  ],
  "overall_verdict": "preference|error|mixed|correct",
  "summary": "one sentence summary in Chinese"
}"""

ERROR_ANNOTATION_SYSTEM_PROMPT = """You are an error annotation specialist for a Chinese accounting / bill-parsing AI system.

For each field that has been identified as a genuine **error**, provide a detailed multi-dimensional annotation. Consider common Chinese financial scenarios:
- 分期付款 (installment payments) — 单期 vs 总额
- 团购/预约 — purchase date vs usage date
- 转账 vs 购物 — category confusion
- 花呗/白条/信用卡 — repayment vs spending
- 二手交易 — income vs expense

Return ONLY valid JSON — no markdown fences, no extra text.

Output format:
{
  "annotations": [
    {
      "field": "string",
      "error_type": "parsing_error|classification_error|inference_error|hallucination|context_missing",
      "severity": "critical|major|minor",
      "description": "what went wrong and why (Chinese)",
      "root_cause": "brief analysis of why the model made this mistake (Chinese)",
      "suggested_fix_direction": "how the prompt could be improved to prevent this (Chinese)"
    }
  ]
}"""

PATTERN_ANALYSIS_SYSTEM_PROMPT = """You are an error pattern analyst for a Chinese accounting / bill-parsing AI system.

Given a collection of annotated errors from the error knowledge base, identify recurring patterns, systemic issues, and correlations.

Focus on patterns specific to Chinese financial habits:
- 线上支付 (mobile payments), 花呗/白条 (BNPL services)
- 团购优惠 (group-buy discounts), 分期账单 (installments)
- 红包/转账 (red packets / transfers)
- 二手闲置 (second-hand sales)

Return ONLY valid JSON — no markdown fences, no extra text.

Output format:
{
  "patterns": [
    {
      "pattern_name": "string",
      "frequency": number,
      "affected_fields": ["field names"],
      "description": "pattern description in Chinese",
      "example_errors": ["error IDs from the knowledge base"],
      "severity_assessment": "how impactful this pattern is (Chinese)"
    }
  ],
  "systemic_issues": ["high-level issues in Chinese"],
  "overall_quality_assessment": "brief assessment in Chinese"
}"""

PROMPT_INSIGHT_SYSTEM_PROMPT = """You are a prompt optimization specialist for a Chinese accounting / bill-parsing AI system.

Given error patterns and quality metrics, generate specific, actionable prompt improvement suggestions so the parsing model can do better next time.

The target model parses natural Chinese text into structured bill records with fields: amount, category, date, merchant.

Return ONLY valid JSON — no markdown fences, no extra text.

Output format:
{
  "insights": [
    {
      "target_field": "which field this improves",
      "issue": "what problem it addresses (Chinese)",
      "suggestion": "specific prompt change recommendation (Chinese)",
      "expected_impact": "what improvement to expect (Chinese)",
      "priority": "high|medium|low"
    }
  ],
  "prompt_additions": ["specific text to add to the prompt (Chinese)"],
  "overall_strategy": "high-level optimization direction (Chinese)"
}"""

# ---------------------------------------------------------------------------
# Helpers — data I/O
# ---------------------------------------------------------------------------

def load_data() -> dict:
    """Load eval_data.json, return dict."""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "samples": [],
            "knowledge_base": {
                "errors": [],
                "patterns": [],
                "stats": {
                    "total_evaluated": 0,
                    "preference_count": 0,
                    "error_count": 0,
                    "ambiguous_count": 0,
                    "accuracy_by_field": {
                        "amount": 1.0, "category": 1.0,
                        "date": 1.0, "merchant": 1.0,
                    },
                    "error_type_distribution": {},
                    "hallucination_rate": 0.0,
                },
            },
        }


def save_data(data: dict) -> None:
    """Persist data to eval_data.json."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Helpers — SSE
# ---------------------------------------------------------------------------

def sse_event(event_type: str, data: dict | str) -> str:
    """Format a Server-Sent Event string."""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


# ---------------------------------------------------------------------------
# Helpers — Claude API
# ---------------------------------------------------------------------------

def call_agent(agent_name: str, system_prompt: str, user_prompt: str,
               max_retries: int = 3) -> dict | None:
    """Call Claude and return parsed JSON. Retries on failure."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = resp.content[0].text
            return parse_json_response(text)
        except Exception as exc:
            print(f"[{agent_name}] attempt {attempt} failed: {exc}")
            if attempt < max_retries:
                time.sleep(1)
    return None


def parse_json_response(text: str) -> dict | None:
    """Multi-strategy JSON extraction from LLM output."""
    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: find first { ... } block
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 4: aggressive cleanup — remove control chars, trailing commas
    cleaned = text.strip()
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"[parse_json] ALL strategies failed. Raw text:\n{text[:500]}")
        return None


# ---------------------------------------------------------------------------
# Helpers — stats
# ---------------------------------------------------------------------------

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
    elif verdict == "correct":
        pass  # no counter change beyond total_evaluated

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

    total_err = sum(dist.values())
    stats["hallucination_rate"] = round(
        dist.get("hallucination", 0) / stats["total_evaluated"], 3
    ) if stats["total_evaluated"] else 0.0


# ---------------------------------------------------------------------------
# Routes — static
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# ---------------------------------------------------------------------------
# Routes — JSON APIs
# ---------------------------------------------------------------------------

@app.route("/api/presets")
def api_presets():
    data = load_data()
    return {"samples": data.get("samples", [])}


@app.route("/api/dashboard")
def api_dashboard():
    data = load_data()
    return data.get("knowledge_base", {}).get("stats", {})


@app.route("/api/knowledge")
def api_knowledge():
    data = load_data()
    return data.get("knowledge_base", {})


# ---------------------------------------------------------------------------
# Routes — /api/evaluate  (SSE)
# ---------------------------------------------------------------------------

@app.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    body = request.get_json(force=True)
    sample_id = body.get("sample_id")
    raw_input = body.get("input", "")
    prediction = body.get("prediction", {})
    user_correction = body.get("user_correction")

    def generate():
        data = load_data()

        # ----- If no correction, mark as correct --------------------------
        if not user_correction:
            result = {
                "sample_id": sample_id,
                "verdict": "correct",
                "classification": None,
                "annotation": None,
            }
            # Persist on sample
            for s in data["samples"]:
                if s["id"] == sample_id:
                    s["eval_result"] = result
                    break
            update_stats(data, {"overall_verdict": "correct"})
            save_data(data)
            yield sse_event("eval_complete", result)
            yield sse_event("dashboard_update", data["knowledge_base"]["stats"])
            return

        # ----- Classification Agent ---------------------------------------
        yield sse_event("agent_start", {"agent": "classification"})

        user_prompt = (
            f"原始输入: {raw_input}\n"
            f"模型预测: {json.dumps(prediction, ensure_ascii=False)}\n"
            f"用户修改: {json.dumps(user_correction, ensure_ascii=False)}"
        )
        classification = call_agent(
            "classification", CLASSIFICATION_SYSTEM_PROMPT, user_prompt
        )
        if not classification:
            yield sse_event("error", {"message": "Classification agent failed"})
            return

        yield sse_event("agent_done", {
            "agent": "classification", "result": classification
        })

        # ----- Error Annotation Agent (if errors exist) -------------------
        annotation = None
        error_fields = [
            m for m in classification.get("modifications", [])
            if m.get("type") == "error"
        ]

        if error_fields:
            yield sse_event("agent_start", {"agent": "annotation"})

            ann_prompt = (
                f"原始输入: {raw_input}\n"
                f"分类结果: {json.dumps(classification, ensure_ascii=False)}\n"
                f"需要标注的错误字段: {json.dumps(error_fields, ensure_ascii=False)}"
            )
            annotation = call_agent(
                "annotation", ERROR_ANNOTATION_SYSTEM_PROMPT, ann_prompt
            )

            if annotation:
                yield sse_event("agent_done", {
                    "agent": "annotation", "result": annotation
                })

                # Persist errors into knowledge base
                for ann in annotation.get("annotations", []):
                    err_id = f"e{len(data['knowledge_base']['errors']) + 1:03d}"
                    error_entry = {
                        "id": err_id,
                        "sample_id": sample_id,
                        "field": ann.get("field", ""),
                        "error_type": ann.get("error_type", "unknown"),
                        "severity": ann.get("severity", "minor"),
                        "description": ann.get("description", ""),
                        "root_cause": ann.get("root_cause", ""),
                        "input_snippet": raw_input[:60],
                        "predicted": str(prediction.get(ann.get("field", ""), "")),
                        "corrected": str(
                            user_correction.get(ann.get("field", ""), "")
                        ),
                    }
                    data["knowledge_base"]["errors"].append(error_entry)

        # ----- Persist result on sample -----------------------------------
        result = {
            "sample_id": sample_id,
            "verdict": classification.get("overall_verdict", "unknown"),
            "classification": classification,
            "annotation": annotation,
        }
        for s in data["samples"]:
            if s["id"] == sample_id:
                s["eval_result"] = result
                break

        update_stats(data, classification)
        save_data(data)

        yield sse_event("eval_complete", result)
        yield sse_event("dashboard_update", data["knowledge_base"]["stats"])

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------------
# Routes — /api/batch  (SSE)
# ---------------------------------------------------------------------------

@app.route("/api/batch", methods=["POST"])
def api_batch():
    body = request.get_json(force=True)
    requested_ids = body.get("sample_ids", [])

    def generate():
        data = load_data()
        samples = data.get("samples", [])

        # Filter if specific IDs requested
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
            user_prompt = (
                f"原始输入: {raw_input}\n"
                f"模型预测: {json.dumps(prediction, ensure_ascii=False)}\n"
                f"用户修改: {json.dumps(user_correction, ensure_ascii=False)}"
            )
            classification = call_agent(
                "classification", CLASSIFICATION_SYSTEM_PROMPT, user_prompt
            )
            if not classification:
                summary["failed"] += 1
                yield sse_event("sample_done", {
                    "sample_id": sid, "verdict": "failed"
                })
                continue

            # --- Annotation (if errors) ---
            annotation = None
            error_fields = [
                m for m in classification.get("modifications", [])
                if m.get("type") == "error"
            ]
            if error_fields:
                ann_prompt = (
                    f"原始输入: {raw_input}\n"
                    f"分类结果: {json.dumps(classification, ensure_ascii=False)}\n"
                    f"需要标注的错误字段: "
                    f"{json.dumps(error_fields, ensure_ascii=False)}"
                )
                annotation = call_agent(
                    "annotation", ERROR_ANNOTATION_SYSTEM_PROMPT, ann_prompt
                )
                if annotation:
                    for ann in annotation.get("annotations", []):
                        err_id = (
                            f"e{len(data['knowledge_base']['errors']) + 1:03d}"
                        )
                        data["knowledge_base"]["errors"].append({
                            "id": err_id,
                            "sample_id": sid,
                            "field": ann.get("field", ""),
                            "error_type": ann.get("error_type", "unknown"),
                            "severity": ann.get("severity", "minor"),
                            "description": ann.get("description", ""),
                            "root_cause": ann.get("root_cause", ""),
                            "input_snippet": raw_input[:60],
                            "predicted": str(
                                prediction.get(ann.get("field", ""), "")
                            ),
                            "corrected": str(
                                user_correction.get(ann.get("field", ""), "")
                            ),
                        })

            verdict = classification.get("overall_verdict", "unknown")
            result = {
                "sample_id": sid,
                "verdict": verdict,
                "classification": classification,
                "annotation": annotation,
            }
            for s in data["samples"]:
                if s["id"] == sid:
                    s["eval_result"] = result
                    break

            update_stats(data, classification)
            summary["evaluated"] += 1
            summary[verdict] = summary.get(verdict, 0) + 1

            yield sse_event("sample_done", result)

        save_data(data)
        yield sse_event("batch_complete", summary)
        yield sse_event("dashboard_update", data["knowledge_base"]["stats"])

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------------
# Routes — /api/analyze  (SSE)
# ---------------------------------------------------------------------------

@app.route("/api/analyze", methods=["POST"])
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

        # ----- Pattern Analysis Agent ------------------------------------
        yield sse_event("agent_start", {"agent": "pattern_analysis"})

        pattern_prompt = (
            f"以下是错误知识库中的所有标注错误 ({len(errors)} 条):\n"
            f"{json.dumps(errors, ensure_ascii=False)}\n\n"
            f"当前质量统计:\n"
            f"{json.dumps(stats, ensure_ascii=False)}\n\n"
            f"请分析这些错误中的规律和系统性问题。"
        )
        pattern_result = call_agent(
            "pattern_analysis", PATTERN_ANALYSIS_SYSTEM_PROMPT, pattern_prompt
        )
        if not pattern_result:
            yield sse_event("error", {"message": "Pattern analysis agent failed"})
            return

        yield sse_event("agent_done", {
            "agent": "pattern_analysis", "result": pattern_result
        })

        # ----- Prompt Insight Agent --------------------------------------
        yield sse_event("agent_start", {"agent": "prompt_insight"})

        insight_prompt = (
            f"错误模式分析结果:\n"
            f"{json.dumps(pattern_result, ensure_ascii=False)}\n\n"
            f"当前质量统计:\n"
            f"{json.dumps(stats, ensure_ascii=False)}\n\n"
            f"已知错误类型分布:\n"
            f"{json.dumps(stats.get('error_type_distribution', {}), ensure_ascii=False)}\n\n"
            f"请给出具体的 prompt 优化建议。"
        )
        insight_result = call_agent(
            "prompt_insight", PROMPT_INSIGHT_SYSTEM_PROMPT, insight_prompt
        )
        if not insight_result:
            yield sse_event("error", {"message": "Prompt insight agent failed"})
            return

        yield sse_event("agent_done", {
            "agent": "prompt_insight", "result": insight_result
        })

        # ----- Persist patterns ------------------------------------------
        kb["patterns"] = pattern_result.get("patterns", kb.get("patterns", []))
        save_data(data)

        yield sse_event("analysis_complete", {
            "patterns": pattern_result,
            "insights": insight_result,
        })

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"[LLM Eval Judge] data file: {DATA_FILE}")
    print(f"[LLM Eval Judge] starting on http://127.0.0.1:8080")
    app.run(host="127.0.0.1", port=8080, debug=True)
