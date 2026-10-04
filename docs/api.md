# JevGuard — API Reference

Interactive docs available at `/docs` (Swagger) and `/redoc` when running.

## Versioning

All endpoints are versioned under `/api/v1/`.

## Endpoints

---

### `GET /health`

Liveness and dependency check.

**Always returns HTTP 200.** The caller interprets `status` and `services`.
This prevents cascading failures in load-balancer health probes.

**Response**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "services": {
    "postgres": "ok",
    "redis": "ok",
    "qdrant": "ok"
  }
}
```

| Field | Values |
|-------|--------|
| `status` | `"ok"` / `"degraded"` |
| `services[*]` | `"ok"` / `"degraded"` / `"error"` |

---

### `POST /api/v1/decisions/route`

Route a request to the appropriate LLM category.

**Request headers**

| Header | Required | Description |
|--------|----------|-------------|
| `X-Request-Id` | No | Client correlation ID. Generated if absent. |

**Request body**

```json
{
  "token_count": 512,
  "has_code": true,
  "has_vision": false,
  "requires_reasoning": false,
  "tool_call_type": null,
  "retrieved_doc_count": 0,
  "query_complexity_score": 0.45
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `token_count` | int ≥ 0 | ✅ | Estimated tokens in the full context |
| `has_code` | bool | No (false) | Request contains code |
| `has_vision` | bool | No (false) | Request contains image input |
| `requires_reasoning` | bool | No (false) | Multi-step reasoning required |
| `tool_call_type` | str / null | No (null) | `delete` / `write` / `read` / `execute` |
| `retrieved_doc_count` | int ≥ 0 | No (0) | Candidate RAG docs retrieved |
| `query_complexity_score` | float [0,1] | No (0.0) | Pre-computed complexity |

**Response**

```json
{
  "request_id": "a1b2c3d4-...",
  "model": "code",
  "confidence": 0.72,
  "reason": "Request contains code content — prefer code-specialized model.",
  "provider": "local_fallback",
  "latency_ms": 4
}
```

| Field | Description |
|-------|-------------|
| `model` | `small` / `large` / `code` / `vision` / `reasoning` |
| `confidence` | Provider confidence [0.0, 1.0] |
| `reason` | Human-readable routing rationale |
| `provider` | `jev` / `local_fallback` |
| `latency_ms` | End-to-end decision latency |

**Error responses**

| Status | Cause |
|--------|-------|
| 422 | Request body validation failed |
| 500 | Unhandled internal error |

## Correlation IDs

Supply `X-Request-Id` on every request for end-to-end tracing.
The value is echoed in the response body and written to the audit log.
Use UUIDs or any unique string ≤ 36 characters.
