from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import RequestIdMiddleware, configure_logging
from app.db.session import engine
from app.api.v1 import router as api_v1_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.echo import router as echo_router

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

        Configure structured logging and close the database pool on shutdown.
    """
    configure_logging()
    log.info("jevguard.starting", version=settings.app_version, env=settings.app_env)
    log.info("jevguard.ready")
    try:
        yield
    finally:
        await engine.dispose()
        log.info("jevguard.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Adaptive AI Decision & Orchestration Platform.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(RequestIdMiddleware)

    # /health — top-level liveness probe (no version prefix)
    app.include_router(health_router)
    app.include_router(echo_router)
    # /api/v1/decisions/... — versioned decision endpoints
    app.include_router(api_v1_router)
    return app


app = create_app()
