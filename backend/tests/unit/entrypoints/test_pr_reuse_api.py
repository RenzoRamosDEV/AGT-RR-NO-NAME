"""Contrato HTTP de la reutilización: `reused` en la ingesta de PRs, `reused_from` en las reviews
y el evento `review.reused` en la línea de tiempo."""

from datetime import UTC, datetime

import httpx

from duelo.domain.events import ReviewCompleted
from duelo.domain.review import Review, ReviewResult
from tests.fakes.api import FakeApi, build_fake_api

T0 = datetime(2026, 1, 1, tzinfo=UTC)
HEADERS = {"X-Ingest-Token": "s3cr3t-token"}
BODY = {
    "project": "acme/widgets",
    "ref": "main",
    "head_sha": "e" * 40,
    "title": "feat: algo",
    "author": "renzo",
    "url": "",
    "diff": "diff --git a/a.py b/a.py\n+x\n",
}


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def _commit_reviewed_by(api: FakeApi, client: httpx.AsyncClient, agents: list[str]) -> str:
    response = await client.post("/ingest/commit", json=BODY, headers=HEADERS)
    change_id = response.json()["change_id"]
    change = next(c for c in api.changes._by_id.values() if str(c.id) == change_id)
    for agent in agents:
        review = Review.succeeded(
            change_id=change.id,
            agent=agent,
            run=1,
            result=ReviewResult(summary="ok", score=9),
            raw_output=None,
            duration_ms=5,
            created_at=T0,
        )
        await api.reviews.add(
            review,
            ReviewCompleted(
                review_id=review.id, change_id=change.id, project_id=api.project.id, agent=agent
            ),
        )
    return change_id


async def test_the_pr_response_says_it_reused_the_reviews_and_the_reads_show_where_from() -> None:
    api = build_fake_api()  # agentes esperados: agent_1 y agent_2
    async with _client(api) as client:
        commit_id = await _commit_reviewed_by(api, client, ["agent_1", "agent_2"])

        pr = await client.post("/ingest/pr", json=BODY, headers=HEADERS)
        pr_id = pr.json()["change_id"]
        detail = (await client.get(f"/changes/{pr_id}")).json()
        listing = (await client.get("/projects/acme/widgets/changes?kind=pr")).json()
        events = (await client.get(f"/changes/{pr_id}/events")).json()

    assert pr.status_code == 202
    assert pr.json() == {
        "change_id": pr_id,
        "diff_truncated": False,
        "created": True,
        "reused": True,
    }
    assert detail["review_status"] == "completed"
    assert [r["reused_from"] for r in detail["reviews"]] == [commit_id, commit_id]
    (item,) = listing["items"]
    assert [r["reused_from"] for r in item["reviews"]] == [commit_id, commit_id]
    assert [e["type"] for e in events] == ["change.created", "review.reused", "review.reused"]
    assert sorted(e["agent"] for e in events[1:]) == ["agent_1", "agent_2"]
    assert all(set(e) == {"id", "type", "created_at", "agent", "review_id"} for e in events)
    assert api.starter.calls == 1  # solo el commit arrancó una review


async def test_the_own_reviews_of_a_change_have_no_origin() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        commit_id = await _commit_reviewed_by(api, client, ["agent_1", "agent_2"])
        detail = (await client.get(f"/changes/{commit_id}")).json()

    assert [r["reused_from"] for r in detail["reviews"]] == [None, None]


async def test_a_pr_is_not_reused_when_the_commit_lacks_an_expected_agent() -> None:
    api = build_fake_api()
    async with _client(api) as client:
        await _commit_reviewed_by(api, client, ["agent_1"])

        pr = await client.post("/ingest/pr", json=BODY, headers=HEADERS)

    assert pr.json()["reused"] is False
    assert api.starter.calls == 2  # el commit y la PR
