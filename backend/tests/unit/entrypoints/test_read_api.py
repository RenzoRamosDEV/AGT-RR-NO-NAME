from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from duelo.application.read_models import ChangeCursor
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.project import Project
from duelo.domain.review import Finding, Review, ReviewResult
from duelo.entrypoints.api.cursor import encode_cursor
from tests.fakes.api import FakeApi, build_fake_api

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def _add_change(
    api: FakeApi, i: int, *, kind: ChangeKind = ChangeKind.COMMIT, project: Project | None = None
) -> Change:
    project = project or api.project
    change = Change.new(
        project_id=project.id,
        kind=kind,
        ref="refs/heads/main",
        head_sha=f"{i:040d}",
        title=f"change {i}",
        author="renzo",
        url="https://example.com",
        diff=f"diff {i}",
        diff_truncated=False,
        created_at=T0 + timedelta(minutes=i),
    )
    event = ChangeCreated(
        change_id=change.id, project_id=project.id, kind=kind.value, head_sha=change.head_sha
    )
    return await api.changes.add(change, event)


# --- GET /projects ---------------------------------------------------------------------


async def test_projects_lists_id_and_slug() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.get("/projects")

    assert response.status_code == 200
    assert response.json() == [{"id": str(api.project.id), "slug": api.project.slug}]


# --- GET /projects/{slug}/changes ------------------------------------------------------


async def test_channel_works_for_slugs_with_a_slash_and_hides_the_diff() -> None:
    api = build_fake_api()
    change = await _add_change(api, 1)

    async with _client(api) as client:
        response = await client.get(f"/projects/{api.project.slug}/changes")

    assert response.status_code == 200
    body = response.json()
    assert body["next_cursor"] is None
    assert [item["id"] for item in body["items"]] == [str(change.id)]
    item = body["items"][0]
    assert "diff" not in item
    assert item["kind"] == "commit" and item["title"] == "change 1" and item["status"] == "pending"


async def test_channel_pagination_follows_next_cursor_without_gaps() -> None:
    api = build_fake_api()
    created = [await _add_change(api, i) for i in range(5)]
    expected = [str(c.id) for c in reversed(created)]
    seen: list[str] = []
    sizes: list[int] = []

    async with _client(api) as client:
        params: dict[str, str] = {"limit": "2"}
        while True:
            body = (await client.get(f"/projects/{api.project.slug}/changes", params=params)).json()
            seen += [i["id"] for i in body["items"]]
            sizes.append(len(body["items"]))
            if body["next_cursor"] is None:
                break
            params = {"limit": "2", "cursor": body["next_cursor"]}

    assert seen == expected and sizes == [2, 2, 1]


async def test_channel_filters_by_kind() -> None:
    api = build_fake_api()
    await _add_change(api, 1)
    pr = await _add_change(api, 2, kind=ChangeKind.PR)

    async with _client(api) as client:
        response = await client.get(f"/projects/{api.project.slug}/changes", params={"kind": "pr"})

    assert [i["id"] for i in response.json()["items"]] == [str(pr.id)]


async def test_channel_of_an_unknown_project_is_404() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.get("/projects/no/existe/changes")

    assert response.status_code == 404
    assert "no/existe" in response.json()["detail"]


async def test_channel_rejects_bad_parameters_with_422() -> None:
    api = build_fake_api()
    base = f"/projects/{api.project.slug}/changes"
    valid_cursor = encode_cursor(ChangeCursor(created_at=T0, id=uuid4()))

    async with _client(api) as client:
        statuses = {
            "limit=0": (await client.get(base, params={"limit": 0})).status_code,
            "limit=101": (await client.get(base, params={"limit": 101})).status_code,
            "limit=100": (await client.get(base, params={"limit": 100})).status_code,
            "limit=1": (await client.get(base, params={"limit": 1})).status_code,
            "kind=x": (await client.get(base, params={"kind": "x"})).status_code,
            "cursor=basura": (await client.get(base, params={"cursor": "basura"})).status_code,
            "cursor ok": (await client.get(base, params={"cursor": valid_cursor})).status_code,
        }

    assert statuses == {
        "limit=0": 422,
        "limit=101": 422,
        "limit=100": 200,
        "limit=1": 200,
        "kind=x": 422,
        "cursor=basura": 422,
        "cursor ok": 200,
    }


async def test_invalid_cursor_422_uses_the_standard_validation_format() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.get(
            f"/projects/{api.project.slug}/changes", params={"cursor": "basura"}
        )

    (error,) = response.json()["detail"]
    assert error["loc"] == ["query", "cursor"] and "cursor" in error["msg"]


# --- GET /changes/{id} -----------------------------------------------------------------


async def test_change_detail_has_diff_and_both_completed_and_failed_reviews() -> None:
    api = build_fake_api()
    change = await _add_change(api, 1)
    ids = {"change_id": change.id, "project_id": api.project.id}
    done = Review.succeeded(
        change_id=change.id,
        agent="agent_1",
        run=1,
        result=ReviewResult(
            summary="todo bien",
            score=8,
            findings=(Finding(severity="low", file="a.py", line=3, message="nit"),),
        ),
        raw_output="SALIDA CRUDA",
        duration_ms=120,
        created_at=T0,
    )
    broken = Review.failed(
        change_id=change.id,
        agent="agent_2",
        run=1,
        error="timeout",
        duration_ms=None,
        created_at=T0,
    )
    await api.reviews.add(done, ReviewCompleted(review_id=done.id, agent="agent_1", **ids))
    await api.reviews.add(
        broken, ReviewFailed(review_id=broken.id, agent="agent_2", error="timeout", **ids)
    )

    async with _client(api) as client:
        response = await client.get(f"/changes/{change.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(change.id) and body["diff"] == "diff 1"
    first, second = body["reviews"]
    assert first["agent"] == "agent_1" and first["status"] == "completed"
    assert (first["summary"], first["score"], first["duration_ms"]) == ("todo bien", 8, 120)
    assert first["findings"] == [{"severity": "low", "file": "a.py", "line": 3, "message": "nit"}]
    assert second["status"] == "failed" and second["error"] == "timeout"
    assert second["summary"] is None and second["score"] is None
    assert "raw_output" not in first and "SALIDA CRUDA" not in response.text


async def test_change_detail_of_an_unknown_id_is_404() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        missing = await client.get(f"/changes/{uuid4()}")
        malformed = await client.get("/changes/no-es-un-uuid")

    assert missing.status_code == 404
    assert malformed.status_code == 422


# --- GET /stats/agents -----------------------------------------------------------------


async def test_stats_are_empty_without_reviews() -> None:
    api = build_fake_api()

    async with _client(api) as client:
        response = await client.get("/stats/agents")

    assert response.status_code == 200 and response.json() == []


async def test_stats_aggregate_by_agent_ignoring_missing_values() -> None:
    api = build_fake_api()
    change = await _add_change(api, 1)
    ids = {"change_id": change.id, "project_id": api.project.id}
    for run, (score, ms) in enumerate([(8, 100), (6, 300)], start=1):
        ok = Review.succeeded(
            change_id=change.id,
            agent="agent_1",
            run=run,
            result=ReviewResult(summary="ok", score=score),
            raw_output=None,
            duration_ms=ms,
            created_at=T0,
        )
        await api.reviews.add(ok, ReviewCompleted(review_id=ok.id, agent="agent_1", **ids))
    bad = Review.failed(
        change_id=change.id, agent="agent_2", run=1, error="x", duration_ms=None, created_at=T0
    )
    await api.reviews.add(bad, ReviewFailed(review_id=bad.id, agent="agent_2", error="x", **ids))

    async with _client(api) as client:
        response = await client.get("/stats/agents")

    assert response.json() == [
        {
            "agent": "agent_1",
            "total": 2,
            "completed": 2,
            "failed": 0,
            "avg_duration_ms": 200.0,
            "avg_score": 7.0,
        },
        {
            "agent": "agent_2",
            "total": 1,
            "completed": 0,
            "failed": 1,
            "avg_duration_ms": None,
            "avg_score": None,
        },
    ]
