# Architecture Decision Log

This file records every significant architectural decision made during
JevGuard's development, in the format recommended by Michael Nygard's
Architecture Decision Records (ADRs).

Entries are append-only.  Superseded decisions are marked **Superseded**
and linked to their replacement.

---

## ADR-001 — DecisionProvider abstraction

**Date:** 2026-09-27
**Status:** Accepted

### Decision
All routing decisions are produced through a `DecisionProvider` abstract
interface.  No application-layer module ever imports `JevDecisionProvider`
or `LocalFallbackDecisionProvider` directly.  The application sees only
`RequestState` → `RoutingDecision`.

### Context
Jev launched in early access on 2026-09-15.  Its API is unversioned and
likely to change.  Tight coupling to the Jev wire format would require
changes throughout the codebase when the API evolves.

### Alternatives considered
1. Call Jev directly from route handlers.  Rejected: any API change touches
   every call site.
2. Use LangChain's abstraction layer.  Rejected: introduces a heavy
   dependency for a thin wrapping concern.

### Trade-offs
- One extra layer of indirection per request.
- `JevClient` is the only module that must be updated when Jev's API changes.

### Consequences
- `jev_client.py` and `jev_provider.py` are the sole holders of Jev's wire
  format knowledge.
- Swapping Jev for another decision model is a one-file change.
- Testing is clean: mock `DecisionProvider`, never `JevClient`.

---

## ADR-002 — Qdrant added to docker-compose from Day 1

**Date:** 2026-09-27
**Status:** Accepted

### Decision
Qdrant is included in `docker-compose.yml` from Phase 1, even though the
RAG Quality Controller is not built until Phase 6.

### Context
Adding a new service to docker-compose mid-project requires every developer
to re-run `docker-compose up` and potentially reset volumes.  The cost of
inclusion from the start is negligible (one extra container, no code impact).

### Alternatives considered
Add Qdrant in Phase 6.  Rejected: causes avoidable migration friction.

### Trade-offs
One unused container running in development for ~5 phases.

### Consequences
Phase 6 can focus on the RAG implementation without any infrastructure work.

---

## ADR-003 — LocalFallbackDecisionProvider is purely deterministic

**Date:** 2026-09-27
**Status:** Accepted

### Decision
The fallback provider uses only rule-based heuristics.  It makes no model
calls, no external network requests, and has no dependencies beyond the
standard library.

### Context
The purpose of the fallback is to guarantee a routing decision when the
primary provider (Jev) is unavailable.  Introducing a secondary model call
in the fallback path defeats this purpose: if Jev is down, another model
API may also be degraded.

### Alternatives considered
Use a small local LLM (via Ollama) as fallback.  Rejected: Ollama may be
unavailable independently of Jev; adds complexity to the fallback path.

### Trade-offs
Lower accuracy than Jev on edge cases.  Acceptable because the fallback
is a graceful degradation path, not the primary path.

### Consequences
- Fallback confidence values are static estimates, not calibrated probabilities.
- Fallback rules must be updated based on Phase 10 evaluation findings.

---

## ADR-004 — Decision audit log is append-only

**Date:** 2026-09-27
**Status:** Accepted

### Decision
`DecisionAuditLog` records are never mutated after insertion.  The table
is treated as an event log.

### Context
Audit logs are used for Phase 10 benchmarking and post-hoc analysis.
Mutating records would make it impossible to reconstruct the exact decision
history used for a given experiment run.

### Alternatives considered
Update records with outcome data (e.g., whether the LLM response was good).
Deferred: outcomes are linked via `request_id` in a separate table, added
when the Response Evaluator (Phase 7) is built.

### Consequences
Storage grows monotonically.  Add a retention/archival policy before
production deployment.

---

## ADR-005 — Confidence thresholds must be validated experimentally

**Date:** 2026-09-27
**Status:** Accepted

### Decision
Initial confidence threshold values (HIGH=0.80, LOW=0.50) are defaults
only.  They are explicitly marked as unvalidated in code and documentation.
Phase 10 (Benchmarking) will determine correct values from evaluation data.

### Context
Confidence thresholds determine when JevGuard escalates to a larger model,
requests human review, or retries.  Arbitrary thresholds can cause
systematic over-escalation (wasted cost) or under-escalation (poor quality).

### Alternatives considered
Use thresholds from published Jev documentation.  Rejected: Jev is new and
no calibration data exists yet for JevGuard's specific use cases.

### Consequences
- Do NOT change threshold defaults based on intuition alone.
- The evaluation framework in Phase 10 must produce calibration curves
  before any threshold is finalised.
- Document all threshold changes with the evaluation evidence that supports
  the change.

---

## ADR-006 — RAG does not require a vector database by definition

**Date:** 2026-09-27
**Status:** Accepted

### Decision
JevGuard's documentation and code acknowledge that RAG can be implemented
with BM25/keyword retrieval, SQL retrieval, graph retrieval, or hybrid
approaches without a vector database.  Qdrant is committed to for
JevGuard's semantic document retrieval use case specifically — not as a
general RAG requirement.

### Context
An early review noted that "RAG always requires a vector DB" is technically
incorrect.  The correct statement is: "semantic similarity retrieval
requires a vector store; JevGuard's RAG module uses semantic retrieval,
therefore it uses Qdrant."

### Consequences
Future RAG variants (BM25, hybrid) do not need to justify why they bypass
Qdrant.  The vector DB is an implementation choice, not a RAG prerequisite.

---

## ADR-008 — Groq replaces TypeSafe AI / Jev as primary decision provider

**Date:** 2026-09-28
**Status:** Accepted

### Decision
`GroqDecisionProvider` (Groq API + LLaMA) is the primary decision provider.
`JevDecisionProvider` remains in the codebase as an optional secondary provider
for users who obtain a TypeSafe AI API key.

### Context
Jev (TypeSafe AI) costs $0.04/1M input tokens — minimal, but not free.
Groq provides 14,400 requests/day on `llama-3.1-8b-instant` at zero cost,
with JSON mode for structured output, making it ideal for the same use case.

Groq also has an OpenAI-compatible API and a well-maintained Python SDK,
reducing integration risk. Temperature=0.0 and JSON mode make responses
sufficiently deterministic for routing decisions.

### Alternatives considered
1. **HuggingFace Inference API** — free but rate-limited to ~100 req/hour. Rejected.
2. **Google Gemini Flash** — free 1,500 req/day. Viable alternative but Groq is faster.
3. **Ollama for decisions** — entirely local, but adds latency for a task
   where the fallback (deterministic rules) is already adequate for degraded mode.
4. **Keep Jev** — small cost, but project requirement is fully free stack. Rejected.

### Trade-offs
- Groq returns natural-language reasoning rather than calibrated probabilities.
  Confidence values from Groq are self-reported estimates, not RLCD outputs like Jev.
- Phase 10 calibration is therefore more important than with Jev.

### Consequences
- `groq_client.py` and `groq_provider.py` are new; `jev_*.py` remain as optional legacy.
- `DECISION_PROVIDER=groq` in `.env` (was `jev`).
- `GROQ_API_KEY` replaces `TYPESAFE_API_KEY`.
- All 37 tests pass with zero API calls (Groq client is mocked in tests).

---

## ADR-009 — Ollama added for Phase 4 local LLM inference

**Date:** 2026-09-28
**Status:** Accepted

### Decision
Ollama is added to `docker-compose.yml` and `configs/model_routing.yaml`
as the Phase 4 LLM inference backend. Groq API is listed as a free alternative.

### Context
All model categories (small, large, code, reasoning, vision) require a concrete
model inference endpoint. Ollama provides fully local, free, open-source inference
via Docker with no API key. Concrete model IDs are now set in `model_routing.yaml`.

### Consequences
- Models must be pulled manually after `docker-compose up`.
- CPU inference is slow for 7B+ models — GPU passthrough in WSL2 recommended.
- Phase 4 implementation reads `model_routing.yaml` to resolve model_id + provider.
