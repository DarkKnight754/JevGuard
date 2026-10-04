# JevGuard — Adaptive AI Decision & Orchestration Platform

> LLMs generate and reason.  Jev makes structured decisions.
> Deterministic code enforces those decisions.

JevGuard is a production-oriented AI infrastructure platform that uses a
decision model ([Jev](https://typesafe.ai)) to dynamically route LLM
workloads, control agent tool execution, evaluate generated responses,
optimise RAG context, and reduce unnecessary model calls.

---

## Architecture

```
User / Client
      │
      ▼
FastAPI Gateway
      │
      ▼
JevGuard Orchestrator
      │
 ┌────┴──────────┐
 ▼               ▼
Router         Guard       Evaluator
 │               │              │
 └───────────────┴──────────────┘
                 │
                 ▼
               JEV                ← structured decisions
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
   Small LLM  Large LLM  Code LLM …
                 │
           Tool System
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
    Search      RAG      Python …
                 │
        PostgreSQL / Audit Logs
                 │
        React Dashboard (Phase 9)
```

## Features (by phase)

| Phase | Module | Status |
|-------|--------|--------|
| 1–2 | FastAPI gateway, DecisionProvider abstraction, PostgreSQL audit log | ✅ |
| 4 | Adaptive LLM Router (Ollama) | 🔲 |
| 5 | Agent Tool-Call Guard | 🔲 |
| 6 | RAG Quality Controller (Qdrant) | 🔲 |
| 7 | LLM Response Evaluator | 🔲 |
| 8 | Context / Token Optimizer | 🔲 |
| 9 | React Observability Dashboard | 🔲 |
| 10 | Benchmarking & Evaluation | 🔲 |
| 11 | Production hardening (OpenTelemetry, rate limiting) | 🔲 |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, Pydantic v2, Uvicorn |
| Decision model | Jev (TypeSafe AI) |
| LLMs | Ollama (local open-weight models) |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Cache | Redis 7 |
| Vector DB | Qdrant (Phase 6) |
| Frontend | React + Vite + Recharts (Phase 9) |
| Infrastructure | Docker, Docker Compose |
| Testing | Pytest, pytest-asyncio, HTTPX |

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/your-username/jevguard.git
cd jevguard
cp .env.example .env
# Edit .env — add TYPESAFE_API_KEY if you have one.
# Leave it empty to run on LocalFallbackDecisionProvider (no external calls).

# 2. Start infrastructure
docker-compose up -d

# 3. Check health
curl http://localhost:8000/health

# 4. Make a routing decision
curl -X POST http://localhost:8000/api/v1/decisions/route \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: my-request-001" \
  -d '{
    "token_count": 512,
    "has_code": true,
    "has_vision": false,
    "requires_reasoning": false,
    "query_complexity_score": 0.4
  }'
```

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v --cov=app --cov-report=term-missing
```

No Docker required for tests — uses SQLite in-memory.

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Evaluation Framework](docs/evaluation.md)
- [Architecture Decision Log](DECISIONS.md)

## Benchmark Results

> Phase 10 not yet complete.  Results will be published here after the
> evaluation suite is run on validated datasets.  See docs/evaluation.md
> for the methodology.

---

## License

MIT
