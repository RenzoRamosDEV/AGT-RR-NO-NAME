import httpx

from tests.fakes.api import build_fake_api


async def _ready(checks: dict) -> httpx.Response:
    api = build_fake_api()
    api.checks.update(checks)
    transport = httpx.ASGITransport(app=api.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/ready")


async def _ok() -> None:
    return None


async def _down() -> None:
    raise ConnectionError("connection refused: postgres://user:password@db/secret")


async def test_ready_is_200_when_every_dependency_responds() -> None:
    response = await _ready({"postgres": _ok, "temporal": _ok})

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_ready_is_503_naming_postgres_while_health_stays_up() -> None:
    api = build_fake_api()
    api.checks.update({"postgres": _down, "temporal": _ok})
    transport = httpx.ASGITransport(app=api.app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        ready = await client.get("/ready")
        health = await client.get("/health")

    assert ready.status_code == 503
    assert ready.json() == {"status": "unavailable", "failing": ["postgres"]}
    assert health.status_code == 200


async def test_ready_is_503_naming_temporal() -> None:
    response = await _ready({"postgres": _ok, "temporal": _down})

    assert response.status_code == 503
    assert response.json()["failing"] == ["temporal"]


async def test_ready_does_not_leak_connection_details() -> None:
    response = await _ready({"postgres": _down})

    assert "password" not in response.text


async def test_ready_names_every_failing_dependency() -> None:
    response = await _ready({"postgres": _down, "temporal": _down})

    assert response.json()["failing"] == ["postgres", "temporal"]


async def test_a_dependency_that_hangs_counts_as_down(monkeypatch) -> None:
    import asyncio

    from review_arena.entrypoints.api.routers import health

    monkeypatch.setattr(health, "READY_TIMEOUT_SECONDS", 0.05)

    async def hang() -> None:
        await asyncio.sleep(5)

    response = await _ready({"temporal": hang})

    assert response.status_code == 503
