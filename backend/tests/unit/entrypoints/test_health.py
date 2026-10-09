import httpx
import pytest

from duelo.entrypoints.api.app import create_app


@pytest.fixture
def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=create_app())
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_health_returns_ok_when_process_is_running(client: httpx.AsyncClient) -> None:
    async with client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_does_not_require_postgres_or_temporal(client: httpx.AsyncClient) -> None:
    """No Postgres/Temporal is configured in this test process at all, and /health
    still responds 200 - it must never reach out to either dependency."""
    async with client:
        response = await client.get("/health")

    assert response.status_code == 200
