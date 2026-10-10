"""Una PR idéntica a un commit ya revisado reutiliza sus reviews y no arranca ningún workflow:
app ASGI real + Postgres real + Temporal de test + workers reales (con FakeAgent)."""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.service import RPCError, RPCStatusCode
from temporalio.testing import WorkflowEnvironment

from duelo.adapters.persistence.models import ReviewModel
from duelo.application.workflow_naming import parent_workflow_id
from tests.e2e.test_ingest_flow import HEADERS, _api, _body, _two, _until, _workers
from tests.integration.conftest import create_project

SHA = "a" * 40


async def _reviews(session_factory: async_sessionmaker, change_id: str) -> list[ReviewModel]:
    async with session_factory() as session:
        rows = await session.execute(
            select(ReviewModel)
            .where(ReviewModel.change_id == UUID(change_id))
            .order_by(ReviewModel.agent)
        )
        return list(rows.scalars())


async def _has_workflow(env: WorkflowEnvironment, workflow_id: str) -> bool:
    try:
        await env.client.get_workflow_handle(workflow_id).describe()
    except RPCError as exc:
        if exc.status is RPCStatusCode.NOT_FOUND:
            return False
        raise
    return True


async def test_a_pr_with_the_same_sha_and_diff_is_born_reviewed_without_a_workflow(
    temporal_env: WorkflowEnvironment, database_url: str, session_factory: async_sessionmaker
) -> None:
    project_id = await create_project(session_factory)
    slug = f"test-{project_id}"

    async with (
        _workers(temporal_env, database_url),
        _api(database_url, temporal_env.client.service_client.config.target_host) as client,
    ):
        commit = await client.post("/ingest/commit", json=_body(slug), headers=HEADERS)
        commit_id = commit.json()["change_id"]
        await _until(lambda: _two(session_factory, commit_id))

        pr = await client.post(
            "/ingest/pr", json=_body(slug, ref="refs/pull/7/head"), headers=HEADERS
        )
        await asyncio.sleep(0.5)  # margen para que un workflow indebido llegara a escribir algo
        pr_id = pr.json()["change_id"]
        detail = await client.get(f"/changes/{pr_id}")
        events = await client.get(f"/changes/{pr_id}/events")
        again = await client.post(
            "/ingest/pr", json=_body(slug, ref="refs/pull/7/head"), headers=HEADERS
        )

    assert pr.status_code == 202 and pr.json()["created"] is True and pr.json()["reused"] is True
    assert pr_id != commit_id
    copies = await _reviews(session_factory, pr_id)
    assert [r.agent for r in copies] == ["agent_1", "agent_2"]  # una por agente, ninguna nueva
    assert {str(r.reused_from_change_id) for r in copies} == {commit_id}
    assert detail.json()["review_status"] == "completed"
    assert all(r["reused_from"] == commit_id for r in detail.json()["reviews"])
    assert [e["type"] for e in events.json()].count("review.reused") == 2
    # El commit sí tiene workflow; la PR no.
    assert await _has_workflow(temporal_env, parent_workflow_id("commit", slug, SHA, project_id, 1))
    assert not await _has_workflow(temporal_env, parent_workflow_id("pr", slug, SHA, project_id, 1))
    # Reenviar la PR no copia nada ni arranca nada.
    assert again.json() == {**pr.json(), "created": False, "reused": True}
    assert len(await _reviews(session_factory, pr_id)) == 2
    assert not await _has_workflow(temporal_env, parent_workflow_id("pr", slug, SHA, project_id, 1))


async def test_a_pr_with_a_different_diff_is_reviewed_normally(
    temporal_env: WorkflowEnvironment, database_url: str, session_factory: async_sessionmaker
) -> None:
    project_id = await create_project(session_factory)
    slug = f"test-{project_id}"

    async with (
        _workers(temporal_env, database_url),
        _api(database_url, temporal_env.client.service_client.config.target_host) as client,
    ):
        commit = await client.post("/ingest/commit", json=_body(slug), headers=HEADERS)
        await _until(lambda: _two(session_factory, commit.json()["change_id"]))

        pr = await client.post(
            "/ingest/pr",
            json=_body(slug, ref="refs/pull/8/head", diff="diff --git a/otro b/otro"),
            headers=HEADERS,
        )
        pr_id = pr.json()["change_id"]
        await _until(lambda: _two(session_factory, pr_id))

    assert pr.json()["created"] is True and pr.json()["reused"] is False
    reviews = await _reviews(session_factory, pr_id)
    assert len(reviews) == 2 and all(r.reused_from_change_id is None for r in reviews)
    assert await _has_workflow(temporal_env, parent_workflow_id("pr", slug, SHA, project_id, 1))


async def test_a_pr_is_reviewed_normally_while_the_commit_is_still_incomplete(
    temporal_env: WorkflowEnvironment, database_url: str, session_factory: async_sessionmaker
) -> None:
    """Límite conocido: la PR no espera al commit; sin todas sus reviews, se revisa con normalidad.
    Sin workers el commit no llega a tener reviews."""
    project_id = await create_project(session_factory)
    slug = f"test-{project_id}"

    async with _api(database_url, temporal_env.client.service_client.config.target_host) as client:
        commit = await client.post("/ingest/commit", json=_body(slug), headers=HEADERS)
        pr = await client.post(
            "/ingest/pr", json=_body(slug, ref="refs/pull/9/head"), headers=HEADERS
        )

    assert commit.status_code == 202 and pr.json()["reused"] is False
    assert await _reviews(session_factory, pr.json()["change_id"]) == []
    assert await _has_workflow(temporal_env, parent_workflow_id("pr", slug, SHA, project_id, 1))
