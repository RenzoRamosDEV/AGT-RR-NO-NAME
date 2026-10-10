import asyncio

import httpx

from duelo.entrypoints.api.routers import health
from tests.fakes.api import build_fake_api


async def _get(checks: dict) -> httpx.Response:
    api = build_fake_api()
    api.checks.update(checks)
    transport = httpx.ASGITransport(app=api.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/health/dependencies")


async def _ok() -> None:
    return None


async def _down() -> None:
    raise ConnectionError("connection refused: postgres://user:password@db/secret")


async def test_all_dependencies_up_reports_ok_with_latency() -> None:
    response = await _get({"postgres": _ok, "temporal": _ok})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["dependencies"]) == {"postgres", "temporal"}
    for dependency in body["dependencies"].values():
        assert dependency["status"] == "ok" and dependency["reason"] is None
        assert isinstance(dependency["latency_ms"], int) and dependency["latency_ms"] >= 0


async def test_a_failing_dependency_is_degraded_with_a_closed_reason_and_no_details() -> None:
    response = await _get({"postgres": _ok, "temporal": _down})

    # Es un diagnóstico: 200 aunque haya fallos (el sondeo para orquestadores es /ready).
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["postgres"]["status"] == "ok"
    assert body["dependencies"]["temporal"]["status"] == "unavailable"
    assert body["dependencies"]["temporal"]["reason"] == "error"
    for secret in ("password", "postgres://", "refused", "secret"):
        assert secret not in response.text


async def test_a_slow_dependency_times_out_without_delaying_the_others(monkeypatch) -> None:
    monkeypatch.setattr(health, "READY_TIMEOUT_SECONDS", 0.05)

    async def slow() -> None:
        await asyncio.sleep(5)

    response = await asyncio.wait_for(_get({"postgres": _ok, "temporal": slow}), timeout=2)

    body = response.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["temporal"]["reason"] == "timeout"
    assert body["dependencies"]["postgres"]["status"] == "ok"
    assert body["dependencies"]["temporal"]["latency_ms"] >= 40  # midió el tiempo esperado


async def test_without_checks_it_is_ok_and_empty() -> None:
    response = await _get({})

    assert response.json() == {
        "status": "ok",
        "dependencies": {},
        "agent_names": ["agent_1", "agent_2"],
    }
