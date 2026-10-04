# JevGuard — Architecture

## Core Principle

> LLMs generate and reason.  Jev makes structured decisions.
> Deterministic application code enforces those decisions.

Jev is a decision layer, not a replacement for LLMs.

## System Overview

```
User / Client Application
         │
         ▼
  ┌─────────────┐
  │   FastAPI   │  API Gateway — validates, routes, correlates requests
  └──────┬──────┘
         │
         ▼
  ┌──────────────────────┐
  │  JevGuard            │  Orchestrator — selects module, coordinates flow
  │  Orchestrator        │
  └──────┬───────────────┘
         │
   ┌─────┼──────────────────┐
   ▼     ▼                  ▼
ROUTER  GUARD           EVALUATOR
   │     │                  │
   └─────┴──────────────────┘
                │
                ▼
         ┌─────────┐
         │   JEV   │  Decision Model — structured, calibrated decisions
         └────┬────┘
              │
   ┌──────────┼───────────┐
   ▼          ▼           ▼
Small LLM  Large LLM  Code LLM  …  (via Ollama — Phase 4)
              │
              ▼
        Tool System        (Phase 5)
              │
   ┌──────────┼───────────┐
   ▼          ▼           ▼
 Search      RAG        Python  …
              │
              ▼
       PostgreSQL / Audit Logs
              │
              ▼
       React Dashboard    (Phase 9)
```

## Component Responsibilities

### API Gateway (FastAPI)
- Request validation (Pydantic)
- Correlation ID propagation (`X-Request-Id`)
- Dependency injection (DB session)
- OpenAPI documentation

### DecisionProvider Abstraction
- `DecisionProvider` (ABC) — the only interface the application sees
- `JevDecisionProvider` — calls TypeSafe AI Jev API
- `LocalFallbackDecisionProvider` — deterministic rules, no network calls
- `DecisionService` — selects provider, handles fallback, writes audit log

### Decision Contracts
- `RequestState` — compact feature-engineered input (never raw text)
- `RoutingDecision` — typed output with model, confidence, reason, provider

### Audit Log (PostgreSQL)
- Append-only `DecisionAuditLog` table
- Every routing decision persisted with full `RequestState` snapshot
- Primary data source for Phase 10 benchmarking

## Module Build Order

| Phase | Module | Status |
|-------|--------|--------|
| 1–2   | FastAPI + PostgreSQL + DecisionProvider | ✅ Complete |
| 3     | DecisionProvider abstraction hardening | ✅ Part of 1–2 |
| 4     | Adaptive LLM Router (Ollama) | 🔲 Planned |
| 5     | Agent Tool-Call Guard | 🔲 Planned |
| 6     | RAG Quality Controller (Qdrant) | 🔲 Planned |
| 7     | LLM Response Evaluator | 🔲 Planned |
| 8     | Context / Token Optimizer | 🔲 Planned |
| 9     | React Observability Dashboard | 🔲 Planned |
| 10    | Benchmarking & Evaluation | 🔲 Planned |
| 11    | Observability & Production Hardening | 🔲 Planned |

## Key Design Constraints

1. **Never** allow Jev → direct destructive action.
   Always: Jev → Deterministic Policy Engine → Action.

2. **Never** call an LLM when deterministic code is sufficient.

3. **Never** use Jev when a simple deterministic rule is sufficient.

4. Confidence thresholds must be validated experimentally (Phase 10).
   Do not set them by intuition.

5. Every provider must implement graceful degradation.
   JevGuard must remain functional if Jev or any LLM is unavailable.
