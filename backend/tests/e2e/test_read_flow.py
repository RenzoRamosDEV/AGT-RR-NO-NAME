"""Lecturas por HTTP sobre lo que dejó la ingesta: canal paginado, detalle y métricas.
Mismo montaje que `test_ingest_flow`: ASGI real + Postgres + Temporal de test + workers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.testing import WorkflowEnvironment

from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.domain.events import ReviewCompleted, ReviewFailed
from duelo.domain.review import Review, ReviewResult
from tests.e2e.test_ingest_flow import (
    HEADERS,
    OPERATOR_TOKEN,
    _api,
    _body,
    _two,
    _until,
    _workers,
)
from tests.integration.conftest import create_project


async def test_a_pr_and_a_commit_show_up_in_the_channel_detail_and_stats(
    temporal_env: WorkflowEnvironment, database_url: str, session_factory: async_sessionmaker
) -> None:
    project_id = await create_project(session_factory)
    slug = f"test-{project_id}"

    async with (
        _workers(temporal_env, database_url),
        _api(database_url, temporal_env.client.service_client.config.target_host) as client,
    ):
        commit = await client.post("/ingest/commit", json=_body(slug), headers=HEADERS)
        pr = await client.post(
            "/ingest/pr", json=_body(slug, ref="refs/pull/7/head"), headers=HEADERS
        )
        commit_again = await client.post("/ingest/commit", json=_body(slug), headers=HEADERS)
        commit_id, pr_id = commit.json()["change_id"], pr.json()["change_id"]
        await _until(lambda: _two(session_factory, commit_id))
        await _until(lambda: _two(session_factory, pr_id))

        projects = (await client.get("/projects")).json()
        first = (await client.get(f"/projects/{slug}/changes", params={"limit": 1})).json()
        second = (
            await client.get(
                f"/projects/{slug}/changes",
                params={"limit": 1, "cursor": first["next_cursor"]},
            )
        ).json()
        only_prs = (await client.get(f"/projects/{slug}/changes", params={"kind": "pr"})).json()
        detail = (await client.get(f"/changes/{pr_id}")).json()
        stats = {s["agent"]: s for s in (await client.get("/stats/agents")).json()}
        scoped = {
            s["agent"]: s
            for s in (await client.get("/stats/agents", params={"project": slug})).json()
        }
        unknown_project = await client.get("/stats/agents", params={"project": "no/existe"})
        events = (await client.get(f"/changes/{commit_id}/events")).json()
        # Los workflows no guardan `raw_output`: el endpoint de operador responde 404 con ellos.
        agent_review_id = detail["reviews"][0]["id"]
        no_raw = await client.get(
            f"/reviews/{agent_review_id}/raw-output", headers={"X-Operator-Token": OPERATOR_TOKEN}
        )

    assert (commit.json()["created"], pr.json()["created"]) == (True, True)
    assert commit_again.json() == {**commit.json(), "created": False}
    assert [i["diff_summary"]["files_changed"] for i in first["items"] + second["items"]] == [1, 1]
    assert detail["diff_summary"]["files"] == [{"path": "x", "additions": 0, "deletions": 0}]
    assert scoped["agent_1"]["total"] == 2 and scoped["agent_2"]["total"] == 2  # PR + commit
    assert unknown_project.status_code == 404
    assert [e["type"] for e in events] == ["change.created", "review.completed", "review.completed"]
    assert sorted(e["agent"] for e in events[1:]) == ["agent_1", "agent_2"]
    assert no_raw.status_code == 404
    assert commit.status_code == pr.status_code == 202 and commit_id != pr_id
    assert {"id": str(project_id), "slug": slug} in projects
    # Mismo sha, dos changes: el PR (más reciente) primero y el commit en la segunda página.
    assert [i["id"] for i in first["items"] + second["items"]] == [pr_id, commit_id]
    assert second["next_cursor"] is None
    assert [i["id"] for i in only_prs["items"]] == [pr_id]
    assert detail["kind"] == "pr" and detail["diff"] == "diff --git a/x b/x"
    assert sorted(r["agent"] for r in detail["reviews"]) == ["agent_1", "agent_2"]
    assert {r["status"] for r in detail["reviews"]} == {"completed"}
    assert all("raw_output" not in r for r in detail["reviews"])
    assert stats["agent_1"]["completed"] >= 2 and stats["agent_2"]["completed"] >= 2


async def test_a_failed_review_is_filterable_retried_and_ends_completed(
    temporal_env: WorkflowEnvironment, database_url: str, session_factory: async_sessionmaker
) -> None:
    """Ingesta sin workers (la ejecución queda en cola), dos reviews fallidas del run 1 puestas
    a mano, y luego `POST /retry`: el run 2 se ejecuta de verdad con los workers y el change
    acaba `completed` con los findings del run 2 (los del run 1 no cuentan)."""
    project_id = await create_project(session_factory)
    slug = f"test-{project_id}"
    address = temporal_env.client.service_client.config.target_host

    async with _api(database_url, address) as client:
        ingested = await client.post(
            "/ingest/commit", json=_body(slug, title="pagos roto"), headers=HEADERS
        )
        change_id = ingested.json()["change_id"]
        pending = (await client.get(f"/changes/{change_id}")).json()["review_status"]
        await _fail_both_agents(session_factory, UUID(change_id), project_id)

        failed = (await client.get(f"/projects/{slug}/changes", params={"status": "failed"})).json()
        searched = (await client.get(f"/projects/{slug}/changes", params={"q": "PAGOS"})).json()
        completed_filter = (
            await client.get(f"/projects/{slug}/changes", params={"status": "completed"})
        ).json()
        health = (await client.get("/health/dependencies")).json()
        no_token = await client.post(f"/changes/{change_id}/retry")
        retried = await client.post(f"/changes/{change_id}/retry", headers=HEADERS)
        too_soon = await client.post(f"/changes/{change_id}/retry", headers=HEADERS)

        async with _workers(temporal_env, database_url):
            await _until(lambda: _two(session_factory, change_id))
            detail = (await client.get(f"/changes/{change_id}")).json()

    assert pending == "pending"
    assert [i["id"] for i in failed["items"]] == [change_id]
    assert failed["items"][0]["review_status"] == "failed"
    assert [i["id"] for i in searched["items"]] == [change_id]
    assert completed_filter["items"] == []
    assert health["status"] == "ok"
    assert set(health["dependencies"]) == {"postgres", "temporal"}
    assert no_token.status_code == 401
    assert retried.status_code == 202 and retried.json() == {"change_id": change_id, "run": 2}
    assert too_soon.status_code == 409  # el run 2 está pendiente: nada que reintentar todavía
    assert detail["run"] == 2 and detail["review_status"] == "completed"
    assert sorted((r["agent"], r["run"], r["status"]) for r in detail["reviews"]) == [
        ("agent_1", 1, "failed"),
        ("agent_1", 2, "completed"),
        ("agent_2", 1, "failed"),
        ("agent_2", 2, "completed"),
    ]
    # FakeAgent aporta un finding `nit` por review: solo cuentan los dos del run 2.
    assert detail["findings_summary"]["total"] == 2
    assert detail["findings_summary"]["by_severity"]["nit"] == 2


async def _fail_both_agents(
    session_factory: async_sessionmaker, change_id: UUID, project_id: UUID
) -> None:
    for agent in ("agent_1", "agent_2"):
        review = Review.failed(
            change_id=change_id,
            agent=agent,
            run=1,
            error="boom",
            duration_ms=None,
            created_at=datetime.now(UTC),
        )
        event = ReviewFailed(
            review_id=review.id,
            change_id=change_id,
            project_id=project_id,
            agent=agent,
            error="boom",
        )
        async with session_factory() as session:
            await SqlAlchemyReviewRepository(session).add(review, event)


async def test_the_operator_reads_raw_output_with_its_own_token_and_nobody_else_can(
    temporal_env: WorkflowEnvironment, database_url: str, session_factory: async_sessionmaker
) -> None:
    project_id = await create_project(session_factory)
    slug = f"test-{project_id}"
    address = temporal_env.client.service_client.config.target_host

    async with _api(database_url, address) as client:
        change_id = UUID(
            (await client.post("/ingest/commit", json=_body(slug), headers=HEADERS)).json()[
                "change_id"
            ]
        )
        review = Review.succeeded(
            change_id=change_id,
            agent="agent_1",
            run=1,
            result=ReviewResult(summary="ok", score=7),
            raw_output="SALIDA CRUDA DEL AGENTE",
            duration_ms=5,
            created_at=datetime.now(UTC),
        )
        event = ReviewCompleted(
            review_id=review.id, change_id=change_id, project_id=project_id, agent="agent_1"
        )
        async with session_factory() as session:
            await SqlAlchemyReviewRepository(session).add(review, event)
        url = f"/reviews/{review.id}/raw-output"

        operator = await client.get(url, headers={"X-Operator-Token": OPERATOR_TOKEN})
        with_ingest_token = await client.get(
            url, headers={"X-Operator-Token": HEADERS["X-Ingest-Token"]}
        )
        anonymous = await client.get(url)
        detail = await client.get(f"/changes/{change_id}")
        events = await client.get(f"/changes/{change_id}/events")

    assert operator.status_code == 200
    assert operator.json() == {"review_id": str(review.id), "raw_output": "SALIDA CRUDA DEL AGENTE"}
    assert operator.headers["cache-control"] == "no-store"
    assert (with_ingest_token.status_code, anonymous.status_code) == (401, 401)
    assert "SALIDA CRUDA" not in detail.text + events.text
