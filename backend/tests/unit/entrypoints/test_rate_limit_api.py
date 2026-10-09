"""Rate limit de POST /ingest/* y /changes/{id}/retry."""

from uuid import uuid4

import httpx

from duelo.adapters.ratelimit.in_memory import InMemoryRateLimiter
from tests.fakes.api import TOKEN, FakeApi, build_fake_api, valid_body

HEADERS = {"X-Ingest-Token": TOKEN}


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _api(limit: int = 2, clock: Clock | None = None) -> FakeApi:
    limiter = InMemoryRateLimiter(limit=limit, window_seconds=60, clock=clock or Clock())
    return build_fake_api(rate_limiter=limiter)


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def test_ingest_beyond_the_limit_is_429_with_retry_after_and_has_no_effect() -> None:
    api = _api(limit=2)
    async with _client(api) as client:
        codes = [
            (
                await client.post(
                    "/ingest/commit", json=valid_body(head_sha=f"{i}" * 40), headers=HEADERS
                )
            ).status_code
            for i in range(3)
        ]
        rejected = await client.post(
            "/ingest/commit", json=valid_body(head_sha="9" * 40), headers=HEADERS
        )

    assert codes == [202, 202, 429]
    assert rejected.status_code == 429
    assert rejected.headers["Retry-After"] == "60"
    assert rejected.json() == {"detail": "Demasiadas peticiones, reintenta más tarde"}
    assert len(api.starter.started) == 2  # lo rechazado no llegó al caso de uso


async def test_commit_and_pr_ingestion_share_the_ingest_budget() -> None:
    api = _api(limit=2)
    async with _client(api) as client:
        first = await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)
        second = await client.post(
            "/ingest/pr", json=valid_body(head_sha="b" * 40), headers=HEADERS
        )
        third = await client.post("/ingest/pr", json=valid_body(head_sha="c" * 40), headers=HEADERS)

    assert [first.status_code, second.status_code, third.status_code] == [202, 202, 429]


async def test_retry_has_its_own_budget_independent_from_ingest() -> None:
    api = _api(limit=1)
    async with _client(api) as client:
        await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)
        ingest_blocked = await client.post(
            "/ingest/commit", json=valid_body(head_sha="b" * 40), headers=HEADERS
        )
        retry_ok = await client.post(f"/changes/{uuid4()}/retry", headers=HEADERS)  # 404: pasa
        retry_blocked = await client.post(f"/changes/{uuid4()}/retry", headers=HEADERS)

    assert ingest_blocked.status_code == 429
    assert retry_ok.status_code == 404
    assert retry_blocked.status_code == 429
    assert "Retry-After" in retry_blocked.headers


async def test_invalid_token_attempts_spend_budget_before_authentication() -> None:
    api = _api(limit=2)
    async with _client(api) as client:
        bad = [
            (
                await client.post(
                    "/ingest/commit", json=valid_body(), headers={"X-Ingest-Token": "mal"}
                )
            ).status_code
            for _ in range(3)
        ]
        valid = await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)

    assert bad == [401, 401, 429]  # la fuerza bruta se corta aunque no acierte
    assert valid.status_code == 429


async def test_the_budget_is_released_as_the_window_slides() -> None:
    clock = Clock()
    api = _api(limit=1, clock=clock)
    async with _client(api) as client:
        await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)
        blocked = await client.post(
            "/ingest/commit", json=valid_body(head_sha="b" * 40), headers=HEADERS
        )
        clock.now = 60
        again = await client.post(
            "/ingest/commit", json=valid_body(head_sha="b" * 40), headers=HEADERS
        )

    assert (blocked.status_code, again.status_code) == (429, 202)


async def test_reads_and_health_are_never_limited() -> None:
    api = _api(limit=1)
    async with _client(api) as client:
        codes = [
            (await client.get(path)).status_code for path in ["/health"] * 3 + ["/projects"] * 3
        ]

    assert codes == [200] * 6


async def test_without_a_limiter_nothing_is_limited() -> None:
    api = build_fake_api()  # RATE_LIMIT_REQUESTS=0 -> sin limitador
    async with _client(api) as client:
        codes = [
            (
                await client.post(
                    "/ingest/commit", json=valid_body(head_sha=f"{i}" * 40), headers=HEADERS
                )
            ).status_code
            for i in range(10)
        ]

    assert codes == [202] * 10
