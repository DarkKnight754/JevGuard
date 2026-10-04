# JevGuard — Adaptive AI Decision & Orchestration Platform

## Mission
Build a production-oriented AI infrastructure project that demonstrates LLM orchestration, model routing, agentic AI safety, RAG quality control, response evaluation, token optimization, observability and benchmarking. It is NOT a domain app (no fintech, healthcare, security product). It is a platform.

Core principle:
LLMs generate and reason. Jev makes bounded, typed decisions. Deterministic application code enforces those decisions.

Jev never replaces the LLM and never directly performs an action.

## Working agreement (read first, every session)
1. Do ONLY the phase I name. Do not create files, tables, endpoints or dependencies that belong to later phases.
2. Keep each phase minimal and testable. Prefer small, readable modules over clever abstractions.
3. When a phase is done: list files changed, give the exact commands to run the tests and acceptance checks, summarize decisions and open questions, then STOP and wait.
4. If something is ambiguous or risky, ask me instead of guessing. Never invent API fields, library behavior or numbers.
5. Before using a library API you are not sure about, check its current official documentation. Use the latest stable versions and pin exact versions in requirements.txt after installing.

## Mandatory decision model: Jev via OpenRouter (verified contract)
- Model: `typesafe/jev-1.13` (pinned; configurable through JEV_MODEL). `~typesafe/jev-latest` is a moving alias, do not use it for benchmarks.
- Endpoint: POST {OPENROUTER_BASE_URL}/alpha/decisions with OPENROUTER_BASE_URL=https://openrouter.ai/api (so the URL is https://openrouter.ai/api/alpha/decisions). This is an ALPHA endpoint. It is NOT the OpenAI-compatible /v1/chat/completions endpoint; chat SDKs do not work with it. Use httpx directly.
- Headers: Authorization: Bearer <OPENROUTER_API_KEY>, Content-Type: application/json
- Request body: {"model": str, "state": object, "questions": {name: question}}
  - noul question: {"type":"noul","instructions":str,"criteria":{"true":str,"false":str}}
  - choice question: {"type":"choice","instructions":str,"criteria":{option_key:description,...}}
  - score question: {"type":"score","instructions":str,"criteria":[ordered level descriptions, index 0 = lowest]}
- Response: {"id","model","provider","answers":{name: answer},"usage":{"input_tokens","output_tokens","cost"}}
  - noul answer: {"type":"noul","noul":<probability of YES, 0..1>} (no confidence field)
  - choice answer: {"type":"choice","choice":str,"confidence":float,"probabilities":{option:float}}
  - score answer: {"type":"score","score":float,"confidence":float,"probabilities":{"0":..,"1":..},"legend":{"0":str,...}}
- Facts that drive design:
  - All questions in ONE request see the same state but cannot see each other's answers. Batch only independent questions. Dependent decisions need separate sequential calls.
  - Context window is 32K tokens. State must be compact features plus truncated snippets.
  - Jev returns NO explanation or reasoning. Log state + answers so decisions can be replayed.
  - Noul has no confidence field: derive confidence = max(p, 1-p) and set confidence_derived=true.
  - Confidence measures how concentrated the probabilities are. It does NOT mean an action is safe.
  - Price is $0.042 per 1M input tokens, output free. usage.cost reports USD per call.
  - Unknown: whether input tokens are billed once or per question. Measure it (Phase 2), do not assume.
- If a response does not match this contract, raise JevResponseError and log it. Never guess missing fields.

## Architecture rules
- Application code depends only on the DecisionProvider interface. Only JevDecisionProvider knows the OpenRouter wire format.
  DecisionProvider
  |- JevDecisionProvider (primary, mandatory, OpenRouter)
  |- LocalFallbackDecisionProvider (deterministic rules; every result has degraded=true; used for outages and the "rules vs Jev" ablation)
- Deterministic policy code has the final word on every action. Jev can only make a decision MORE restrictive, never grant what policy denies. Most restrictive wins.
- Tools marked destructive ALWAYS require stored human approval, regardless of Jev.
- Do not use an LLM when code is enough. Do not use Jev when a simple rule is enough (e.g. image attached -> vision model needs no Jev call).
- Fail-safe defaults: guard fails CLOSED; router falls back to a middle tier; RAG falls back to top-k by retriever score; evaluator returns the answer flagged `unevaluated`.
- Confidence bands (auto / verify / human-or-fallback) live in YAML configs, never in code. Placeholder thresholds must be labeled PLACEHOLDER with `calibrated: false`. Never describe a threshold as "safe" until Phase 10 calibration supports it.
- Token efficiency from day one: compute features before calling Jev, ask many independent questions per state in ONE call, cache with Redis, avoid sending the same context twice, never call an LLM unnecessarily.
- Log every important decision (state hash, state, question, answer, provider, model version, latency, tokens, cost, cached, degraded).
- Use LangGraph ONLY where a stateful bounded loop truly helps (Phase 7 generate-evaluate-retry; optionally Phase 5 human-approval pause). Plain async Python elsewhere.

## Stack
Backend: Python 3.12+, FastAPI, Pydantic v2 (pydantic-settings), SQLAlchemy 2.x async with asyncpg, Alembic, httpx, structlog.
Data: PostgreSQL, Redis, Qdrant (only from Phase 6).
LLMs: Ollama (local) and OpenRouter chat completions behind an LLMProvider interface.
Frontend: React + Vite + Recharts (Phase 9).
Infra: Docker, Docker Compose. Tests: pytest, pytest-asyncio, httpx (respx or MockTransport for mocking). Lint: ruff. Secrets: .env only.

## Repository layout
jevguard/
  backend/
    app/
      main.py
      api/          (routers: health, chat, tools, metrics, reviews)
      core/         (config, logging, errors, security)
      models/       (SQLAlchemy models)
      schemas/      (Pydantic request/response schemas)
      services/     (orchestrator, router, tool_guard, rag, evaluator, context_optimizer, llm providers)
      decision/     (DecisionProvider, Jev client, fallback, question registry)
      db/           (session, migrations)
    tests/
    requirements.txt
  frontend/         (Vite React app)
  benchmarks/       (harness code, added in Phase 10)
  scripts/          (smoke test, billing probe, run_benchmark, calibrate_thresholds, make_report)
  data/{raw,processed,sample,sandbox}/
  configs/{model_routing,tool_guard,rag_quality,response_quality}.yaml
  docker/
  docker-compose.yml, .env.example, .gitignore, README.md, LICENSE

## Coding conventions
- Fully type-annotated, async I/O, small functions, no global mutable state.
- Pydantic models for every external boundary (HTTP in/out, Jev wire format, config).
- Typed domain errors (JevHTTPError, JevTimeout, JevResponseError, PolicyDenied, ...). No bare except.
- Timeouts on every outbound call. Retries only for 429, 5xx and timeouts, with jitter and a cap. Never retry 4xx.
- Secrets: SecretStr, loaded from environment only. Never log, print, echo or commit keys. Redact PII and secrets before logging or sending state to Jev.
- SQL only through SQLAlchemy (parameterized). Alembic migration for every schema change.

## Testing rules
- Tests never hit the real network by default. Mock OpenRouter and Ollama.
- Live tests are marked `@pytest.mark.live` and skipped unless I run `pytest -m live`.
- Every phase ships tests for its failure paths (timeouts, malformed responses, fallback, degraded flag).
- Safety invariants have explicit tests (e.g. "Jev says SAFE but policy denies -> blocked").

## Benchmark honesty rules
- Never fabricate, estimate from memory or hand-type benchmark numbers, in code, docs or the README.
- README result tables are generated from files in data/processed/benchmarks/<run_id>/ by scripts/make_report.py. Anything not yet measured says "not yet measured".
- JevGuard arms must include Jev's own latency, tokens and cost in their totals.
- Dashboard shows real database values or an empty state, never demo numbers.