"""
Shared pytest fixtures.

Database
--------
Tests use SQLite (aiosqlite) in-memory so no Postgres is needed locally.
SQLAlchemy's dialect-agnostic types (String, Float, JSON, Integer, DateTime)
work identically on both backends.
Note: JSONB (Postgres-specific) in DecisionAuditLog falls back to JSON on
SQLite — acceptable for unit tests, Postgres is used in CI and production.

Provider
--------
All route tests use DECISION_PROVIDER=local_fallback so no network calls are
made and no TYPESAFE_API_KEY is required.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ── Override settings BEFORE importing the app ────────────────────────────────
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GATEWAY_API_KEY", "phase-one-test-key")
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("DECISION_PROVIDER", "local_fallback")  # tests never call Groq
os.environ.setdefault("TYPESAFE_API_KEY", "")

from app.api.v1.routes.health import get_redis  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app                  # noqa: E402

_TEST_DB_URL = os.environ["TEST_DATABASE_URL"]


class TestRedis:
    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    """
    Per-test in-memory SQLite session.
    Creates all tables on entry, drops them on exit.
    """
    engine = create_async_engine(_TEST_DB_URL, echo=False)

    # Register models
    import app.models.audit  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncClient:
    """
    AsyncClient wired to the FastAPI app with the DB dependency overridden
    to use the in-memory test session.
    """
    async def _override_db():
        yield db_session

    async def _override_redis():
        yield TestRedis()

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = _override_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
