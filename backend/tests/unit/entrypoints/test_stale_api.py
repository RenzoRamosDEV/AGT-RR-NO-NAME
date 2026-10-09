"""`stale` en el listado y el detalle: reloj inyectado, sin dormir."""

from datetime import UTC, datetime, timedelta

import httpx

from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.review import Review, ReviewResult
from tests.fakes.api import FakeApi, build_fake_api

T0 = datetime(2026, 1, 1, tzinfo=UTC)
THRESHOLD = 1800


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def _change(api: FakeApi, sha: str, *, age: timedelta, clock: Clock) -> Change:
    change = Change.new(
        project_id=api.project.id,
        kind=ChangeKind.COMMIT,
        ref="r",
        head_sha=sha * 40,
        title=f"change {sha}",
        author="a",
        url="u",
        diff="d",
        diff_truncated=False,
        created_at=clock.now - age,
    )
    event = ChangeCreated(
        change_id=change.id, project_id=api.project.id, kind="commit", head_sha=change.head_sha
    )
    return await api.changes.add(change, event)


async def _review(api: FakeApi, change: Change, agent: str, *, fail: bool = False) -> None:
    ids = {"change_id": change.id, "project_id": api.project.id, "agent": agent}
    common = {"change_id": change.id, "agent": agent, "run": change.run, "created_at": T0}
    if fail:
        review = Review.failed(error="boom", duration_ms=None, **common)
        await api.reviews.add(review, ReviewFailed(review_id=review.id, error="boom", **ids))
    else:
        review = Review.succeeded(
            result=ReviewResult(summary="ok", score=5, findings=()),
            raw_output="x",
            duration_ms=1,
            **common,
        )
        await api.reviews.add(review, ReviewCompleted(review_id=review.id, **ids))


async def _listed(client: httpx.AsyncClient, api: FakeApi) -> dict[str, bool]:
    response = await client.get(f"/projects/{api.project.slug}/changes")
    assert response.status_code == 200, response.text
    return {item["title"]: item["stale"] for item in response.json()["items"]}


async def test_list_and_detail_mark_only_old_waiting_changes_as_stale() -> None:
    clock = Clock(T0)
    api = build_fake_api(clock=clock, stale_after_seconds=THRESHOLD)
    old_pending = await _change(api, "1", age=timedelta(seconds=THRESHOLD + 1), clock=clock)
    old_running = await _change(api, "2", age=timedelta(hours=5), clock=clock)
    await _review(api, old_running, "a")  # una de dos: running
    fresh = await _change(api, "3", age=timedelta(seconds=THRESHOLD), clock=clock)  # en el límite
    old_done = await _change(api, "4", age=timedelta(days=30), clock=clock)
    await _review(api, old_done, "a")
    await _review(api, old_done, "b")
    old_failed = await _change(api, "5", age=timedelta(days=30), clock=clock)
    await _review(api, old_failed, "a", fail=True)
    await _review(api, old_failed, "b", fail=True)

    async with _client(api) as client:
        listed = await _listed(client, api)
        detail = {
            c.id: (await client.get(f"/changes/{c.id}")).json()["stale"]
            for c in (old_pending, old_running, fresh, old_done, old_failed)
        }

    assert listed == {
        "change 1": True,
        "change 2": True,
        "change 3": False,  # exactamente en el umbral todavía no
        "change 4": False,  # completed
        "change 5": False,  # failed
    }
    assert [detail[c.id] for c in (old_pending, old_running, fresh, old_done, old_failed)] == [
        True,
        True,
        False,
        False,
        False,
    ]


async def test_stale_follows_the_injected_clock() -> None:
    clock = Clock(T0)
    api = build_fake_api(clock=clock, stale_after_seconds=THRESHOLD)
    change = await _change(api, "1", age=timedelta(seconds=10), clock=clock)

    async with _client(api) as client:
        before = (await client.get(f"/changes/{change.id}")).json()["stale"]
        clock.now += timedelta(seconds=THRESHOLD)
        after = (await client.get(f"/changes/{change.id}")).json()["stale"]

    assert (before, after) == (False, True)


async def test_stale_is_only_a_diagnostic_it_does_not_touch_the_change() -> None:
    clock = Clock(T0)
    api = build_fake_api(clock=clock, stale_after_seconds=THRESHOLD)
    change = await _change(api, "1", age=timedelta(days=1), clock=clock)

    async with _client(api) as client:
        response = await client.get(f"/changes/{change.id}")

    assert response.json()["stale"] is True
    assert response.json()["run"] == change.run
    assert api.starter.started == {}  # no se relanzó nada
