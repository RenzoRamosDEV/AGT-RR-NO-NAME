"""Lecturas por HTTP sobre lo que dejó la ingesta: canal paginado, detalle y métricas.
Mismo montaje que `test_ingest_flow`: ASGI real + Postgres + Temporal de test + workers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.testing import WorkflowEnvironment

from tests.e2e.test_ingest_flow import HEADERS, _api, _body, _two, _until, _workers
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
