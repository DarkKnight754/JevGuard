from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request import RequestRecord


async def test_echo_rejects_missing_or_invalid_api_key(client: AsyncClient) -> None:
    missing_key = await client.post("/v1/echo")
    invalid_key = await client.post(
        "/v1/echo", headers={"X-API-Key": "incorrect"}
    )

    assert missing_key.status_code == 401
    assert invalid_key.status_code == 401


async def test_echo_writes_request_record(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    response = await client.post(
        "/v1/echo", headers={"X-API-Key": "phase-one-test-key"}
    )

    assert response.status_code == 200
    request_id = uuid.UUID(response.json()["request_id"])
    record = await db_session.get(RequestRecord, request_id)

    assert record is not None
    assert record.endpoint == "/v1/echo"
    assert record.mode == "echo"
    assert record.status == "accepted"
    assert record.latency_ms >= 0
    assert record.meta == {}