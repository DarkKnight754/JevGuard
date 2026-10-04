from __future__ import annotations

import secrets
import time
import uuid

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.request import RequestRecord
from app.schemas.echo import EchoResponse

log = structlog.get_logger(__name__)
router = APIRouter()


async def require_gateway_key(x_api_key: str | None = Header(default=None)) -> None:
    configured_key = settings.gateway_api_key.get_secret_value()
    if x_api_key is None or not secrets.compare_digest(x_api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


@router.post(
    "/v1/echo",
    response_model=EchoResponse,
    dependencies=[Depends(require_gateway_key)],
    tags=["Gateway"],
)
async def echo(db: AsyncSession = Depends(get_db)) -> EchoResponse:
    started_at = time.perf_counter()
    request_id = uuid.uuid4()
    record = RequestRecord(
        id=request_id,
        endpoint="/v1/echo",
        mode="echo",
        status="accepted",
        latency_ms=0,
        meta={},
    )
    db.add(record)
    await db.flush()
    record.latency_ms = round((time.perf_counter() - started_at) * 1000)
    log.info("gateway.echo.accepted", request_record_id=str(request_id))
    return EchoResponse(request_id=str(request_id))