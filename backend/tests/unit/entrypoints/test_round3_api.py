"""API de la ronda 3: resumen del diff, stats por proyecto, `created`, eventos y salida cruda."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.review import Review, ReviewResult
from tests.fakes.api import OPERATOR_TOKEN, TOKEN, FakeApi, build_fake_api, valid_body

T0 = datetime(2026, 1, 1, tzinfo=UTC)
INGEST = {"X-Ingest-Token": TOKEN}
OPERATOR = {"X-Operator-Token": OPERATOR_TOKEN}
DIFF = "diff --git a/a.py b/a.py\n@@ -1 +1,2 @@\n-x\n+y\n+z\n"


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def _add_change(api: FakeApi, diff: str = DIFF) -> Change:
    change = Change.new(
        project_id=api.project.id,
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha="1" * 40,
        title="t",
        author="a",
        url="https://example.com",
        diff=diff,
        diff_truncated=False,
        created_at=T0,
    )
    event = ChangeCreated(
        change_id=change.id, project_id=api.project.id, kind="commit", head_sha=change.head_sha
    )
    return await api.changes.add(change, event)


async def _add_review(
    api: FakeApi, change: Change, agent: str, *, raw_output: str | None = "SALIDA CRUDA", fail=False
) -> Review:
    ids = {"change_id": change.id, "project_id": api.project.id, "agent": agent}
    if fail:
        review = Review.failed(
            change_id=change.id,
            agent=agent,
            run=1,
            error="Traceback: token=SECRETO",
            duration_ms=None,
            created_at=T0,
        )
        event = ReviewFailed(review_id=review.id, error="Traceback: token=SECRETO", **ids)
    else:
        review = Review.succeeded(
            change_id=change.id,
            agent=agent,
            run=1,
            result=ReviewResult(summary="ok", score=7),
            raw_output=raw_output,
            duration_ms=10,
            created_at=T0,
        )
        event = ReviewCompleted(review_id=review.id, **ids)
    return await api.reviews.add(review, event)


# --- diff_summary -------------------------------------------------------------------------


async def test_listing_and_detail_expose_the_diff_summary() -> None:
    api = build_fake_api()
    change = await _add_change(api)
    expected = {
        "files_changed": 1,
        "additions": 2,
        "deletions": 1,
        "files": [{"path": "a.py", "additions": 2, "deletions": 1}],
    }

    async with _client(api) as client:
        listing = await client.get(f"/projects/{api.project.slug}/changes")
        detail = await client.get(f"/changes/{change.id}")

    assert listing.json()["items"][0]["diff_summary"] == expected
    assert detail.json()["diff_summary"] == expected


async def test_ingesting_a_diff_stores_its_summary_without_a_second_request() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        created = await client.post("/ingest/commit", json=valid_body(diff=DIFF), headers=INGEST)
        detail = await client.get(f"/changes/{created.json()['change_id']}")

    assert detail.json()["diff_summary"]["additions"] == 2


# --- created ------------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/ingest/commit", "/ingest/pr"])
async def test_ingest_reports_created_then_not_created_with_the_same_status(path: str) -> None:
    api = build_fake_api()

    async with _client(api) as client:
        first = await client.post(path, json=valid_body(), headers=INGEST)
        again = await client.post(path, json=valid_body(), headers=INGEST)

    assert (first.status_code, again.status_code) == (202, 202)
    assert (first.json()["created"], again.json()["created"]) == (True, False)
    assert first.json()["change_id"] == again.json()["change_id"]


# --- GET /stats/agents?project= -------------------------------------------------------------


async def test_stats_can_be_scoped_to_a_project_and_default_to_global() -> None:
    api = build_fake_api()
    change = await _add_change(api)
    await _add_review(api, change, "agent_1")

    async with _client(api) as client:
        scoped = await client.get("/stats/agents", params={"project": api.project.slug})
        everyone = await client.get("/stats/agents")

    assert [s["agent"] for s in scoped.json()] == ["agent_1"]
    assert scoped.json() == everyone.json()


async def test_stats_of_an_unknown_project_is_404_and_bad_values_are_422() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        unknown = await client.get("/stats/agents", params={"project": "no/hay"})
        nul = await client.get("/stats/agents", params={"project": "a\x00b"})
        too_long = await client.get("/stats/agents", params={"project": "x" * 256})
        longest = await client.get("/stats/agents", params={"project": "x" * 255})

    assert unknown.status_code == 404 and "no/hay" in unknown.json()["detail"]
    assert (nul.status_code, too_long.status_code) == (422, 422)
    assert nul.json()["detail"][0]["loc"] == ["query", "project"]
    assert longest.status_code == 404  # válido de forma, pero no existe


# --- GET /changes/{id}/events --------------------------------------------------------------


async def test_events_are_listed_in_order_without_error_text_or_raw_output() -> None:
    api = build_fake_api()
    change = await _add_change(api)
    done = await _add_review(api, change, "agent_1")
    failed = await _add_review(api, change, "agent_2", fail=True)

    async with _client(api) as client:
        response = await client.get(f"/changes/{change.id}/events")

    assert response.status_code == 200
    events = response.json()
    assert [(e["type"], e["agent"], e["review_id"]) for e in events] == [
        ("change.created", None, None),
        ("review.completed", "agent_1", str(done.id)),
        ("review.failed", "agent_2", str(failed.id)),
    ]
    assert set(events[1]) == {"id", "type", "created_at", "agent", "review_id"}
    assert "SECRETO" not in response.text and "SALIDA CRUDA" not in response.text


async def test_events_of_an_unknown_or_malformed_change_id() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        missing = await client.get(f"/changes/{uuid4()}/events")
        malformed = await client.get("/changes/no-es-uuid/events")

    assert (missing.status_code, malformed.status_code) == (404, 422)


# --- GET /reviews/{id}/raw-output -----------------------------------------------------------


async def test_raw_output_is_returned_to_the_operator_without_caching() -> None:
    api = build_fake_api()
    review = await _add_review(api, await _add_change(api), "agent_1")

    async with _client(api) as client:
        response = await client.get(f"/reviews/{review.id}/raw-output", headers=OPERATOR)

    assert response.status_code == 200
    assert response.json() == {"review_id": str(review.id), "raw_output": "SALIDA CRUDA"}
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "headers",
    [{}, {"X-Operator-Token": "otro-token-de-16-chars"}, {"X-Operator-Token": TOKEN}, INGEST],
    ids=["sin cabecera", "token incorrecto", "token de ingesta", "cabecera de ingesta"],
)
async def test_raw_output_rejects_anything_but_the_operator_token(headers: dict[str, str]) -> None:
    api = build_fake_api()
    review = await _add_review(api, await _add_change(api), "agent_1")

    async with _client(api) as client:
        response = await client.get(f"/reviews/{review.id}/raw-output", headers=headers)

    assert response.status_code == 401
    assert "SALIDA CRUDA" not in response.text


async def test_raw_output_accepts_a_non_ascii_token_comparison_without_crashing() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.get(
            f"/reviews/{uuid4()}/raw-output", headers={"X-Operator-Token": "tókén-ñ".encode()}
        )

    assert response.status_code == 401


async def test_raw_output_is_disabled_with_404_for_everyone_when_no_operator_token() -> None:
    api = build_fake_api(operator_token=None)
    review = await _add_review(api, await _add_change(api), "agent_1")

    async with _client(api) as client:
        bare = await client.get(f"/reviews/{review.id}/raw-output")
        guessing = await client.get(f"/reviews/{review.id}/raw-output", headers=OPERATOR)

    assert (bare.status_code, guessing.status_code) == (404, 404)
    assert "SALIDA CRUDA" not in bare.text + guessing.text


async def test_raw_output_is_404_for_unknown_failed_or_output_less_reviews() -> None:
    api = build_fake_api()
    change = await _add_change(api)
    failed = await _add_review(api, change, "agent_2", fail=True)
    empty = await _add_review(api, change, "agent_3", raw_output=None)

    async with _client(api) as client:
        statuses = [
            (await client.get(f"/reviews/{rid}/raw-output", headers=OPERATOR)).status_code
            for rid in (uuid4(), failed.id, empty.id)
        ]
        malformed = await client.get("/reviews/no-es-uuid/raw-output", headers=OPERATOR)

    assert statuses == [404, 404, 404] and malformed.status_code == 422


async def test_the_public_detail_still_hides_raw_output_when_the_operator_endpoint_exists() -> None:
    api = build_fake_api()
    change = await _add_change(api)
    await _add_review(api, change, "agent_1")

    async with _client(api) as client:
        detail = await client.get(f"/changes/{change.id}")
        events = await client.get(f"/changes/{change.id}/events")

    assert "SALIDA CRUDA" not in detail.text + events.text
