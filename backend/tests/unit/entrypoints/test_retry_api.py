import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.review import Review, ReviewResult
from tests.fakes.api import TOKEN, FakeApi, build_fake_api
from tests.fakes.review_starter import FakeReviewStarter

HEADERS = {"X-Ingest-Token": TOKEN}
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def _change_with_reviews(api: FakeApi, *outcomes: bool) -> Change:
    """Crea un change y una review por resultado (True = falla), con agentes a, b, ..."""
    change = Change.new(
        project_id=api.project.id,
        kind=ChangeKind.COMMIT,
        ref="r",
        head_sha="d" * 40,
        title="t",
        author="a",
        url="u",
        diff="d",
        diff_truncated=False,
        created_at=NOW,
    )
    event = ChangeCreated(
        change_id=change.id, project_id=api.project.id, kind="commit", head_sha=change.head_sha
    )
    await api.changes.add(change, event)
    for agent, fail in zip("ab", outcomes, strict=False):
        ids = {"change_id": change.id, "project_id": api.project.id, "agent": agent}
        common = {"change_id": change.id, "agent": agent, "run": 1, "created_at": NOW}
        if fail:
            review = Review.failed(error="boom", duration_ms=None, **common)
            await api.reviews.add(review, ReviewFailed(review_id=review.id, error="boom", **ids))
        else:
            review = Review.succeeded(
                result=ReviewResult(summary="ok", score=1),
                raw_output=None,
                duration_ms=1,
                **common,
            )
            await api.reviews.add(review, ReviewCompleted(review_id=review.id, **ids))
    return change


async def test_retrying_a_failed_review_is_202_and_advances_run() -> None:
    api = build_fake_api()
    change = await _change_with_reviews(api, True, True)

    async with _client(api) as client:
        response = await client.post(f"/changes/{change.id}/retry", headers=HEADERS)
        detail = (await client.get(f"/changes/{change.id}")).json()

    assert response.status_code == 202
    assert response.json() == {"change_id": str(change.id), "run": 2}
    assert detail["run"] == 2 and detail["review_status"] == "pending"
    assert api.starter.calls == 1


async def test_retry_requires_the_ingest_token_and_has_no_effects_without_it() -> None:
    api = build_fake_api()
    change = await _change_with_reviews(api, True, True)

    async with _client(api) as client:
        missing = await client.post(f"/changes/{change.id}/retry")
        wrong = await client.post(f"/changes/{change.id}/retry", headers={"X-Ingest-Token": "no"})

    assert (missing.status_code, wrong.status_code) == (401, 401)
    assert api.starter.calls == 0
    assert (await api.changes.get(change.id)).run == 1  # type: ignore[union-attr]


async def test_retry_of_a_completed_pending_or_running_review_is_409() -> None:
    api = build_fake_api()
    completed = await _change_with_reviews(api, False, False)
    api2 = build_fake_api()
    pending = await _change_with_reviews(api2)
    api3 = build_fake_api()
    running = await _change_with_reviews(api3, True)

    codes = []
    for fake, change in ((api, completed), (api2, pending), (api3, running)):
        async with _client(fake) as client:
            response = await client.post(f"/changes/{change.id}/retry", headers=HEADERS)
        codes.append((response.status_code, fake.starter.calls))

    assert codes == [(409, 0)] * 3


async def test_retry_names_the_blocking_status_in_the_409() -> None:
    api = build_fake_api()
    change = await _change_with_reviews(api, False, False)

    async with _client(api) as client:
        response = await client.post(f"/changes/{change.id}/retry", headers=HEADERS)

    assert "completed" in response.json()["detail"]


async def test_retry_of_an_unknown_change_is_404_and_a_malformed_id_422() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        missing = await client.post(f"/changes/{uuid4()}/retry", headers=HEADERS)
        malformed = await client.post("/changes/x/retry", headers=HEADERS)

    assert (missing.status_code, malformed.status_code) == (404, 422)


async def test_retry_with_temporal_down_is_503_and_run_stays_so_it_can_be_repeated() -> None:
    api = build_fake_api(starter=FakeReviewStarter(fail=True))
    change = await _change_with_reviews(api, True, True)

    async with _client(api) as client:
        response = await client.post(f"/changes/{change.id}/retry", headers=HEADERS)

    assert response.status_code == 503
    assert (await api.changes.get(change.id)).run == 1  # type: ignore[union-attr]
    api.starter.fail = False
    async with _client(api) as client:
        again = await client.post(f"/changes/{change.id}/retry", headers=HEADERS)
    assert again.status_code == 202


async def test_two_simultaneous_retries_are_both_202_with_one_execution() -> None:
    api = build_fake_api(starter=FakeReviewStarter(yield_on_start=True))
    change = await _change_with_reviews(api, True, True)

    async with _client(api) as client:
        first, second = await asyncio.gather(
            client.post(f"/changes/{change.id}/retry", headers=HEADERS),
            client.post(f"/changes/{change.id}/retry", headers=HEADERS),
        )

    assert (first.status_code, second.status_code) == (202, 202)
    assert first.json()["run"] == second.json()["run"] == 2
    assert len(api.starter.started) == 1
