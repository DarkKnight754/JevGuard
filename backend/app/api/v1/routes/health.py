from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthResponse, ReadyResponse

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Observability"],
    summary="Liveness check",
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
    try:
        yield client
    finally:
        await client.aclose()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    tags=["Observability"],
    summary="Dependency readiness check",
)
async def ready_check(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> ReadyResponse:
    checks = {"postgres": "ok", "redis": "ok"}
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        log.warning("ready.postgres_unavailable", error_type=type(exc).__name__)
        checks["postgres"] = "error"

    try:
        await redis.ping()
    except (RedisError, OSError) as exc:
        log.warning("ready.redis_unavailable", error_type=type(exc).__name__)
        checks["redis"] = "error"

    if any(check != "ok" for check in checks.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks},
        )
    return ReadyResponse(status="ready", checks=checks)
