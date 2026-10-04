from httpx import AsyncClient


async def test_health_is_liveness_only(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


async def test_ready_checks_postgres_and_redis(client: AsyncClient) -> None:
    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"postgres": "ok", "redis": "ok"},
    }


async def test_ready_returns_503_when_postgres_is_down(client: AsyncClient) -> None:
    from fastapi import Request
    from sqlalchemy.exc import SQLAlchemyError

    from app.db.session import get_db

    class OfflineDatabase:
        async def execute(self, statement: object) -> None:
            raise SQLAlchemyError("database unavailable")

    async def override_db(request: Request):
        yield OfflineDatabase()

    client._transport.app.dependency_overrides[get_db] = override_db
    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["checks"]["postgres"] == "error"
