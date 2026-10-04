# JevGuard — Evaluation Framework

> Do not claim improvements.  Measure them.

This document defines the evaluation methodology for Phase 10.
All benchmark results in the README must be produced by running the
evaluation suite described here — never fabricated.

---

## Experimental Design

Two systems are compared on the same query set:

**Baseline**
Every request → same large LLM → final answer.
No routing, no evaluation, no guard.

**JevGuard**
Request → Jev → routing / evaluation / guard → appropriate model/workflow.

---

## Metrics

### Decision quality
| Metric | Description |
|--------|-------------|
| Routing accuracy | % of requests routed to the correct model category |
| Guard precision | TP / (TP + FP) on blocked tool calls |
| Guard recall | TP / (TP + FN) on blocked tool calls |
| Evaluator agreement | % agreement with human judgement on response quality |

### Efficiency
| Metric | Description |
|--------|-------------|
| Latency (p50, p95, p99) | End-to-end request latency (ms) |
| Input tokens | Total input tokens consumed |
| Output tokens | Total output tokens consumed |
| LLM calls | Number of model invocations |
| Estimated cost | USD at published provider rates |
| Retry rate | % of requests that triggered a retry |
| Escalation rate | % of requests escalated to a larger model or human |

### RAG quality (Phase 6+)
| Metric | Description |
|--------|-------------|
| Context precision | Relevant retrieved docs / total retrieved docs |
| Context recall | Relevant retrieved docs / total relevant docs |
| Answer quality (RAGAS) | Faithfulness, answer relevance, context relevance |

---

## Test Datasets

Assembled before Phase 10 begins.  Do not construct datasets after seeing
results — this introduces selection bias.

| Category | Source | Size | Purpose |
|----------|--------|------|---------|
| Simple Q&A | TriviaQA (HuggingFace) | 500 | Tests small-model routing |
| Code tasks | HumanEval (HuggingFace) | 164 | Tests code-model routing |
| Long document | QuALITY (HuggingFace) | 300 | Tests context optimizer |
| Tool-call safety | Synthetic (hand-written) | 100 | Tests agent guard |
| Multi-hop reasoning | HotpotQA (HuggingFace) | 200 | Tests reasoning routing |

Synthetic tool-call safety cases should be written before Phase 5 begins
and stored in `data/sample/tool_guard_cases.jsonl`.

---

## Confidence Calibration

Confidence threshold validation procedure:

1. Collect Jev decisions with ground-truth outcomes on ≥500 requests.
2. For each threshold T in [0.5, 0.55, 0.60, … 0.95]:
   - Compute accuracy of decisions with confidence ≥ T
   - Compute coverage (% of requests above threshold)
3. Plot calibration curve (confidence vs. observed accuracy).
4. Select HIGH_CONFIDENCE_THRESHOLD as the point where
   `observed_accuracy ≥ 0.90` AND `coverage ≥ 0.60`.
5. Select LOW_CONFIDENCE_THRESHOLD as the point where
   `observed_accuracy < 0.70` OR `coverage drops below 0.20`.
6. Document the selected thresholds with the calibration plot in this file.

**Current status:** Unvalidated defaults (HIGH=0.80, LOW=0.50).
Update this section with calibration results from Phase 10.

---

## Reporting Requirements

The README's benchmark section must include:

- Dataset sizes and sources
- Exact model versions used (Jev model ID, Ollama model IDs)
- Hardware (CPU/GPU, RAM)
- Date the benchmark was run
- Raw numbers (not cherry-picked)
- Confidence intervals where applicable
- Known limitations and failure modes

Fabricated or cherry-picked numbers make the project untrustworthy.
The goal is honest measurement, not impressive marketing.
