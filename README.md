# LLM Eval Judge

> Evaluation is harder than generation. Anyone can call an API. Knowing whether the output is actually good — that's the real product problem.

An LLM-as-a-Judge system that automatically evaluates model output quality by distinguishing **personal preference adjustments** from **genuine model errors**, building a structured error knowledge base, and generating actionable prompt optimization insights through a data flywheel.

## Product Insight

### The Evaluation Gap

In 2026, every AI product ships with a model. Few ship with a quality system. The result: teams fly blind — they can see that users are correcting outputs, but they can't tell whether those corrections mean "the model is wrong" or "the user just prefers it differently."

This distinction matters enormously:

| User modifies "餐饮" → "咖啡" | User modifies amount ¥499 → ¥166.33 |
|-------------------------------|--------------------------------------|
| **Preference** — both are correct; the user just has a finer-grained category system | **Error** — the model confused total price with installment amount |
| Action: Learn this user's preferences | Action: Fix the prompt/model |
| Metric: Don't count as error | Metric: Count as parsing failure |

Treating all corrections as errors inflates your error rate and sends you chasing phantom bugs. Treating real errors as preferences means you never fix them. **The Judge's job is to tell the difference.**

### The Data Flywheel

This isn't a one-shot evaluation tool. It's a **continuous quality improvement loop**:

```
Model outputs predictions
         │
         ▼
Users correct some fields
         │
         ▼
┌─ AI Judge ─────────────────────┐
│  Classification Agent:          │
│  Is this preference or error?   │
│                                 │
│  Annotation Agent:              │
│  What type? How severe?         │
└────────────┬────────────────────┘
             │
             ▼
┌─ Knowledge Base ───────────────┐
│  Structured error catalog       │
│  + Pattern detection            │
└────────────┬────────────────────┘
             │
             ▼
┌─ Prompt Insight Agent ─────────┐
│  "Add installment detection     │
│   logic to amount parsing"      │
└────────────┬────────────────────┘
             │
             ▼
    Improved prompts → Better outputs → Fewer errors
                            ↑                │
                            └────────────────┘
```

**Every user correction makes the system smarter** — not through fine-tuning, but through structured error analysis feeding back into prompt engineering.

## Architecture

### 4-Agent Pipeline

```
User Correction Data
  (input + prediction + correction)
            │
            ▼
┌─ Classification Agent ──────────────┐
│  For each modified field:            │
│  • preference — user habit           │
│  • error — model mistake             │
│  • ambiguous — unclear               │
│  Confidence score + reasoning        │
└───────────────┬──────────────────────┘
                │
        ┌───────┴───────┐
        │               │
   Has errors?      All preference
        │               │
        ▼           Return as-is
┌─ Annotation Agent ──────────────────┐
│  For each error:                     │
│  • error_type (5 categories)         │
│  • severity (critical/major/minor)   │
│  • root_cause analysis               │
│  • suggested fix direction           │
└───────────────┬──────────────────────┘
                │
                ▼
        Knowledge Base Updated
        (errors + stats + patterns)
```

### On-Demand Analysis (Separate Trigger)

```
Knowledge Base (accumulated errors)
            │
            ▼
┌─ Pattern Analysis Agent ────────────┐
│  Identifies recurring error patterns │
│  Correlates across fields & types    │
│  Assesses systemic issues            │
└───────────────┬──────────────────────┘
                │
                ▼
┌─ Prompt Insight Agent ──────────────┐
│  Generates specific prompt changes   │
│  Prioritizes by impact               │
│  Provides text additions to try      │
└─────────────────────────────────────┘
```

### Evaluation Dimensions

| Dimension | Values | Purpose |
|-----------|--------|---------|
| **Modification Type** | preference / error / ambiguous | Core classification |
| **Field** | amount / category / date / merchant | Which prediction field |
| **Error Type** | parsing_error / classification_error / inference_error / hallucination / context_missing | Root cause taxonomy |
| **Severity** | critical / major / minor | Prioritization |

### Quality Metrics Dashboard

| Metric | What It Tracks | Why It Matters |
|--------|---------------|----------------|
| Accuracy by Field | Per-field correct rate | Identifies weakest prediction areas |
| Error Type Distribution | Breakdown of error causes | Guides where to invest prompt engineering |
| Preference vs. Error Ratio | True error rate (excluding preferences) | Prevents inflated error counts |
| Hallucination Rate | % of fabricated outputs | Safety-critical for financial data |

## Demo Scenario: Smart Accounting

The demo simulates quality evaluation for a bill parsing model that predicts 4 fields from natural language input:

| Field | Task | Common Error Patterns |
|-------|------|-----------------------|
| **Amount** | Parse monetary value | Installment vs. total, "人均" vs. actual spend |
| **Category** | Classify spending type | Transfer vs. purchase, granularity mismatch |
| **Date** | Infer transaction date | Group-buy usage date vs. purchase date |
| **Merchant** | Identify merchant | Hallucinated names, platform vs. actual store |

### 18 Pre-loaded Samples

Covering: correct predictions (no change), preference modifications (finer categories), genuine errors (amount parsing, date inference, merchant hallucination), ambiguous cases, and edge cases (installments, transfers, group-buys).

## Interactive Demo

- **Left Panel**: Batch evaluate button, manual input form, clickable sample list with color-coded status
- **Center**: Evaluation result cards with 4-field grid (color-coded by verdict), error annotations with root cause
- **Right Panel**: Live quality dashboard — accuracy bars, error distribution, pattern cards, prompt optimization insights

### Demo Flow

1. Click **"Batch Evaluate All"** — watch the Judge process all 18 samples via SSE streaming
2. See the dashboard update in real-time — accuracy bars, error counts, type distribution
3. Click **"Analyze Patterns"** — Pattern Analysis + Prompt Insight agents identify systemic issues
4. Read the **prompt optimization suggestions** — specific, actionable changes ranked by priority
5. Try manual evaluation with custom inputs

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| **AI** | Claude API (Haiku 4.5) | Fast inference for per-sample evaluation at scale |
| **Backend** | Flask + SSE | Streaming progress for batch operations |
| **Frontend** | Vanilla HTML/CSS/JS | Zero build step, modular components, portfolio-friendly |
| **Knowledge Base** | JSON file | Structured storage without database overhead |
| **Testing** | pytest | Unit + integration tests for agents, eval store, and routes |

## Project Structure

```
llm-eval-judge/
├── app.py                          # Flask entry point — registers blueprints, serves frontend
├── config.py                       # Shared constants (model, paths)
│
├── agents/                         # 4 evaluation agents, each independently iterable
│   ├── base.py                     # Claude API calls, JSON parsing, prompt loading
│   ├── classification.py           # Preference vs Error classification
│   ├── annotation.py               # Error annotation with root cause analysis
│   ├── pattern_analysis.py         # Cross-sample error pattern detection
│   └── prompt_insight.py           # Prompt optimization suggestion generation
│
├── prompts/                        # System prompts as standalone markdown (decoupled from code)
│   ├── classification.md
│   ├── annotation.md
│   ├── pattern_analysis.md
│   └── prompt_insight.md
│
├── eval_store/                     # Evaluation data & knowledge base management
│   ├── store.py                    # JSON persistence (load / save)
│   └── stats.py                    # Quality metrics calculator (accuracy, distribution, rates)
│
├── events/
│   └── stream.py                   # Server-Sent Events formatting
│
├── routes/                         # Flask Blueprints — one per pipeline
│   ├── evaluate.py                 # POST /api/evaluate (Classification → Annotation)
│   ├── batch.py                    # POST /api/batch (batch evaluation)
│   ├── analyze.py                  # POST /api/analyze (Pattern Analysis → Prompt Insight)
│   └── dashboard.py                # GET /api/presets, /api/dashboard, /api/knowledge
│
├── static/                         # Frontend assets
│   ├── index.html                  # HTML skeleton
│   ├── css/style.css               # All styles
│   └── js/
│       ├── api.js                  # SSE streaming client
│       ├── app.js                  # State management + initialization
│       └── components/
│           ├── sample-panel.js     # Left panel: sample list, single/manual evaluation
│           ├── eval-results.js     # Center: result cards, batch progress, analysis
│           └── dashboard.js        # Right panel: quality metrics, patterns, insights
│
├── tests/                          # pytest test suite
│   ├── test_agents.py              # JSON parsing, prompt loading
│   ├── test_eval_store.py          # Data persistence, stats calculation
│   └── test_routes.py              # API endpoint integration tests
│
└── data/
    └── eval_data.json              # Runtime persistent state (gitignored)
```

## Quick Start

```bash
git clone https://github.com/jianizhang123-creator/llm-eval-judge.git
cd llm-eval-judge

pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here

python app.py                       # → http://localhost:8080

# Run tests
pytest tests/ -v
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Preference vs. Error as core classification | Conflating them inflates error rates and misdirects prompt engineering effort |
| 5-type error taxonomy | Specific enough to be actionable, general enough to cover all cases |
| Severity levels per error | Not all errors matter equally — hallucination is critical, minor category differences are not |
| Separate analysis trigger | Pattern analysis is expensive and should run on accumulated data, not per-sample |
| Prompt Insight as structured output | Vague "improve the prompt" is useless; specific text additions are actionable |
| Pre-seeded knowledge base | Dashboard shows meaningful data from the start, demonstrating the flywheel concept |

---

*Built to validate that LLM output quality can be systematically measured, categorized, and improved through automated evaluation — turning user corrections from a black box into a structured data flywheel for continuous prompt optimization.*
