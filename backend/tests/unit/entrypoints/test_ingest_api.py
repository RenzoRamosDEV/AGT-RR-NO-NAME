import logging

import httpx
import pytest

from review_arena.domain.change import MAX_HEAD_SHA, MAX_REF, MAX_URL
from review_arena.entrypoints.api import auth
from tests.fakes.api import TOKEN, FakeApi, build_fake_api, valid_body
from tests.fakes.review_starter import FakeReviewStarter

HEADERS = {"X-Ingest-Token": TOKEN}


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


def _no_effects(api: FakeApi) -> None:
    assert api.changes.persisted_events == []
    assert api.starter.calls == 0


async def test_valid_commit_returns_202_with_the_change_id() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)

    assert response.status_code == 202
    assert response.json() == {
        "change_id": str(api.changes.persisted_events[0].change_id),
        "diff_truncated": False,
    }
    assert api.starter.calls == 1


async def test_resending_the_same_commit_returns_the_same_change_without_duplicates() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        first = await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)
        second = await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)

    assert first.json()["change_id"] == second.json()["change_id"]
    assert len(api.changes.persisted_events) == 1
    assert len(api.starter.started) == 1


async def test_unknown_project_is_404_without_effects() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.post(
            "/ingest/commit", json=valid_body(project="otro/repo"), headers=HEADERS
        )

    assert response.status_code == 404
    _no_effects(api)


async def test_oversized_diff_is_truncated_and_flagged() -> None:
    api = build_fake_api(max_diff_chars=10)

    async with _client(api) as client:
        response = await client.post(
            "/ingest/commit", json=valid_body(diff="x" * 50), headers=HEADERS
        )

    assert response.status_code == 202
    assert response.json()["diff_truncated"] is True
    stored = next(iter(api.changes._by_id.values()))
    assert stored.diff == "x" * 10


async def test_temporal_down_is_503_and_a_later_retry_starts_the_review() -> None:
    api = build_fake_api(starter=FakeReviewStarter(fail=True))

    async with _client(api) as client:
        down = await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)
        api.starter.fail = False
        retry = await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)

    assert down.status_code == 503
    assert retry.status_code == 202
    assert len(api.changes.persisted_events) == 1
    assert len(api.starter.started) == 1


# --- Autenticación (8.2) ---------------------------------------------------------------


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Ingest-Token": ""},
        {"X-Ingest-Token": " "},
        {"X-Ingest-Token": f" {TOKEN}"},
        {"X-Ingest-Token": f"{TOKEN} "},
        {"X-Ingest-Token": TOKEN.upper()},
        {"X-Ingest-Token": TOKEN[:-1]},
        {"X-Ingest-Token": TOKEN + "x"},
        {"X-Ingest-Token": "ñandú-ünïcode".encode()},
        {"Authorization": f"Bearer {TOKEN}"},
    ],
    ids=lambda h: repr(h)[:40],
)
async def test_missing_or_wrong_token_is_401_without_effects(
    headers: dict[str, str | bytes],
) -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.post("/ingest/commit", json=valid_body(), headers=headers)

    assert response.status_code == 401
    _no_effects(api)


async def test_the_token_is_compared_in_constant_time(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[bytes, bytes]] = []
    real = auth.hmac.compare_digest

    def spy(a: bytes, b: bytes) -> bool:
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(auth.hmac, "compare_digest", spy)
    api = build_fake_api()

    async with _client(api) as client:
        await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)

    assert calls == [(TOKEN.encode(), TOKEN.encode())]


async def test_health_and_ready_do_not_require_a_token() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        health = await client.get("/health")
        ready = await client.get("/ready")

    assert health.status_code == 200 and ready.status_code == 200


# --- Seguridad de la API (8.3) ---------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        b"{no es json",
        b"[]",
        b'"texto"',
        b"",
        b'{"project": 5}',
        b'{"project": "acme/widgets"}',
        b'{"project": "acme/widgets", "ref": "r", "head_sha": ["a"]}',
    ],
)
async def test_malformed_bodies_are_422_with_no_trace_and_no_effects(payload: bytes) -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.post(
            "/ingest/commit",
            content=payload,
            headers={**HEADERS, "Content-Type": "application/json"},
        )

    assert response.status_code == 422
    assert "Traceback" not in response.text and TOKEN not in response.text
    _no_effects(api)


async def test_unknown_fields_are_rejected() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.post("/ingest/commit", json=valid_body(extra="x"), headers=HEADERS)

    assert response.status_code == 422
    _no_effects(api)


@pytest.mark.parametrize(
    "overrides",
    [
        {"head_sha": "a" * (MAX_HEAD_SHA + 1)},
        {"ref": "r" * (MAX_REF + 1)},
        {"url": "u" * (MAX_URL + 1)},
        {"head_sha": "a\x00b"},
        {"ref": "refs/\x00"},
        {"project": ""},
        {"head_sha": ""},
    ],
    ids=lambda o: next(iter(o)),
)
async def test_values_beyond_the_limits_are_422_without_effects(overrides: dict) -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.post(
            "/ingest/commit", json=valid_body(**overrides), headers=HEADERS
        )

    assert response.status_code == 422
    _no_effects(api)


@pytest.mark.parametrize(
    "hostile",
    ["'; DROP TABLE changes; --", "<script>alert(1)</script>", "𝕌𝕟𝕚𝕔𝕠𝕕𝕖 ‮ rtl ☃", "%00 ../../etc"],
)
async def test_hostile_text_in_free_fields_is_stored_as_plain_data(hostile: str) -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.post(
            "/ingest/commit",
            json=valid_body(title=hostile, author=hostile, diff=hostile),
            headers=HEADERS,
        )

    assert response.status_code == 202
    stored = next(iter(api.changes._by_id.values()))
    assert stored.title == hostile and stored.diff == hostile


async def test_neither_the_token_nor_internals_leak_into_errors_or_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    api = build_fake_api(starter=FakeReviewStarter(fail=True))
    caplog.set_level(logging.DEBUG)

    async with _client(api) as client:
        wrong = await client.post(
            "/ingest/commit", json=valid_body(), headers={"X-Ingest-Token": "intento-secreto"}
        )
        failed = await client.post("/ingest/commit", json=valid_body(), headers=HEADERS)

    for response in (wrong, failed):
        assert TOKEN not in response.text
        assert "Traceback" not in response.text and "FakeReviewStarter" not in response.text
    assert TOKEN not in caplog.text
