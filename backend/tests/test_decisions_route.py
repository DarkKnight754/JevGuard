"""
Integration tests for POST /api/v1/decisions/route.

Uses the in-memory SQLite DB (conftest) and LocalFallbackDecisionProvider
(DECISION_PROVIDER=local_fallback in conftest env).  No network calls.

Tests verify:
  - HTTP contract (status, schema, field types)
  - Correct model routing for key request shapes
  - Audit record written to DB for every request
  - X-Request-Id header is respected and echoed back
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import DecisionAuditLog


ROUTE = "/api/v1/decisions/route"


def simple_body(**overrides) -> dict:
    base = {
        "token_count": 300,
        "has_code": False,
        "has_vision": False,
        "requires_reasoning": False,
        "tool_call_type": None,
        "retrieved_doc_count": 0,
        "query_complexity_score": 0.2,
    }
    base.update(overrides)
    return base


# ── HTTP contract ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_route_returns_200(client: AsyncClient):
    response = await client.post(ROUTE, json=simple_body())
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_response_schema_complete(client: AsyncClient):
    response = await client.post(ROUTE, json=simple_body())
    data = response.json()
    assert "request_id" in data
    assert "model" in data
    assert "confidence" in data
    assert "provider" in data
    assert "latency_ms" in data
    assert isinstance(data["confidence"], float)
    assert isinstance(data["latency_ms"], int)


@pytest.mark.asyncio
async def test_invalid_body_returns_422(client: AsyncClient):
    """Missing required token_count field."""
    response = await client.post(ROUTE, json={"has_code": True})
    assert response.status_code == 422


# ── Routing correctness ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vision_request_routes_to_vision(client: AsyncClient):
    body = simple_body(has_vision=True)
    response = await client.post(ROUTE, json=body)
    assert response.json()["model"] == "vision"


@pytest.mark.asyncio
async def test_large_context_routes_to_large(client: AsyncClient):
    body = simple_body(token_count=10_000)
    response = await client.post(ROUTE, json=body)
    assert response.json()["model"] == "large"


@pytest.mark.asyncio
async def test_code_request_routes_to_code(client: AsyncClient):
    body = simple_body(has_code=True)
    response = await client.post(ROUTE, json=body)
    assert response.json()["model"] == "code"


@pytest.mark.asyncio
async def test_default_request_routes_to_small(client: AsyncClient):
    response = await client.post(ROUTE, json=simple_body())
    assert response.json()["model"] == "small"


@pytest.mark.asyncio
async def test_provider_is_local_fallback_in_test_env(client: AsyncClient):
    response = await client.post(ROUTE, json=simple_body())
    assert response.json()["provider"] == "local_fallback"


# ── Correlation ID ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_x_request_id_is_echoed(client: AsyncClient):
    custom_id = "test-req-abc-123"
    response = await client.post(
        ROUTE,
        json=simple_body(),
        headers={"x-request-id": custom_id},
    )
    assert response.json()["request_id"] == custom_id


@pytest.mark.asyncio
async def test_request_id_auto_generated_when_absent(client: AsyncClient):
    response = await client.post(ROUTE, json=simple_body())
    data = response.json()
    assert data["request_id"]
    assert len(data["request_id"]) > 0


# ── Audit log ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_record_written(client: AsyncClient, db_session: AsyncSession):
    custom_id = "audit-test-001"
    await client.post(
        ROUTE,
        json=simple_body(),
        headers={"x-request-id": custom_id},
    )
    result = await db_session.execute(
        select(DecisionAuditLog).where(DecisionAuditLog.request_id == custom_id)
    )
    record = result.scalar_one_or_none()
    assert record is not None
    assert record.provider == "local_fallback"
    assert record.model_selected in {"small", "large", "code", "vision", "reasoning"}
    assert 0.0 <= record.confidence <= 1.0
    assert record.input_state is not None


@pytest.mark.asyncio
async def test_audit_records_multiple_requests(client: AsyncClient, db_session: AsyncSession):
    for i in range(3):
        await client.post(
            ROUTE,
            json=simple_body(),
            headers={"x-request-id": f"multi-test-{i}"},
        )
    result = await db_session.execute(select(DecisionAuditLog))
    records = result.scalars().all()
    assert len(records) == 3
