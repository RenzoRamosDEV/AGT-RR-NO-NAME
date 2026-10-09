"""Flujos críticos por HTTP: app ASGI real + Postgres real + Temporal de test + workers reales
(con FakeAgent). Es el criterio de 'hecho' de la Fase 2."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.testing import WorkflowEnvironment

from duelo.adapters.persistence.models import ChangeModel, EventModel, ReviewModel
from duelo.composition import build_api_dependencies
from duelo.config import Settings
from duelo.entrypoints.api.app import create_app
from duelo.worker import build_workers
from tests.integration.conftest import create_project

TOKEN = "e2e-token"
HEADERS = {"X-Ingest-Token": TOKEN}
DEAD_TEMPORAL = "127.0.0.1:1"


def _body(slug: str, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "project": slug,
        "ref": "refs/heads/main",
        "head_sha": "a" * 40,
        "title": "fix: algo",
        "author": "renzo",
        "url": "https://example.com/c/1",
        "diff": "diff --git a/x b/x",
    }
    body.update(overrides)
    return body


@asynccontextmanager
async def _api(database_url: str, temporal_address: str) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(
        ingest_token=TOKEN, database_url=database_url, temporal_address=temporal_address
    )
    deps = build_api_dependencies(settings)
    transport = httpx.ASGITransport(app=create_app(settings, deps))
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        await deps.close()


@asynccontextmanager
async def _workers(env: WorkflowEnvironment, database_url: str) -> AsyncIterator[None]:
    settings = Settings(ingest_token=TOKEN, database_url=database_url)
    platform, agents = build_workers(env.client, settings)
    async with platform, agents:
        yield


async def _until(predicate: Callable[[], object], seconds: float = 20) -> None:
    for _ in range(int(seconds / 0.1)):
        if await predicate():  # type: ignore[misc]
            return
        await asyncio.sleep(0.1)
    raise AssertionError("la condición no se cumplió a tiempo")


def _review_count(session_factory: async_sessionmaker, change_id: str):
    async def count() -> int:
        async with session_factory() as session:
            return (
                await session.execute(
                    select(func.count())
                    .select_from(ReviewModel)
                    .where(
                        ReviewModel.change_id == UUID(change_id), ReviewModel.status == "completed"
                    )
                )
            ).scalar_one()

    return count


async def _count(session_factory: async_sessionmaker, model, *where) -> int:
    async with session_factory() as session:
        return (
            await session.execute(select(func.count()).select_from(model).where(*where))
        ).scalar_one()


async def test_post_commit_ends_with_two_reviews_and_resending_adds_none(
    temporal_env: WorkflowEnvironment, database_url: str, session_factory: async_sessionmaker
) -> None:
    project_id = await create_project(session_factory)
    slug = f"test-{project_id}"

    async with (
        _workers(temporal_env, database_url),
        _api(database_url, temporal_env.client.service_client.config.target_host) as client,
    ):
        first = await client.post("/ingest/commit", json=_body(slug), headers=HEADERS)
        change_id = first.json()["change_id"]
        await _until(lambda: _two(session_factory, change_id))

        again = await client.post("/ingest/commit", json=_body(slug), headers=HEADERS)
        await asyncio.sleep(0.5)

    assert first.status_code == 202 and again.status_code == 202
    assert again.json()["change_id"] == change_id
    assert await _count(session_factory, ChangeModel, ChangeModel.project_id == project_id) == 1
    assert (
        await _count(
            session_factory,
            EventModel,
            EventModel.project_id == project_id,
            EventModel.type == "change.created",
        )
        == 1
    )
    assert await _count(session_factory, ReviewModel, ReviewModel.change_id == UUID(change_id)) == 2


async def _two(session_factory: async_sessionmaker, change_id: str) -> bool:
    return await _review_count(session_factory, change_id)() == 2


async def test_unknown_project_is_404_and_leaves_no_trace(
    temporal_env: WorkflowEnvironment, database_url: str, session_factory: async_sessionmaker
) -> None:
    before = await _count(session_factory, ChangeModel)

    async with _api(database_url, temporal_env.client.service_client.config.target_host) as client:
        response = await client.post(
            "/ingest/commit", json=_body("no-existe/proyecto"), headers=HEADERS
        )

    assert response.status_code == 404
    assert await _count(session_factory, ChangeModel) == before


async def test_temporal_down_is_503_then_resending_starts_the_review(
    temporal_env: WorkflowEnvironment, database_url: str, session_factory: async_sessionmaker
) -> None:
    project_id = await create_project(session_factory)
    slug = f"test-{project_id}"

    async with _api(database_url, DEAD_TEMPORAL) as client:
        down = await client.post("/ingest/commit", json=_body(slug), headers=HEADERS)
        ready = await client.get("/ready")

    assert down.status_code == 503
    assert ready.status_code == 503 and "temporal" in ready.json()["failing"]
    assert await _count(session_factory, ChangeModel, ChangeModel.project_id == project_id) == 1

    async with (
        _workers(temporal_env, database_url),
        _api(database_url, temporal_env.client.service_client.config.target_host) as client,
    ):
        retry = await client.post("/ingest/commit", json=_body(slug), headers=HEADERS)
        change_id = retry.json()["change_id"]
        await _until(lambda: _two(session_factory, change_id))
        ready = await client.get("/ready")

    assert retry.status_code == 202
    assert await _count(session_factory, ChangeModel, ChangeModel.project_id == project_id) == 1
    assert ready.status_code == 200


async def test_oversized_diff_is_stored_truncated(
    temporal_env: WorkflowEnvironment, database_url: str, session_factory: async_sessionmaker
) -> None:
    project_id = await create_project(session_factory)
    settings_limit = 200_000

    async with _api(database_url, temporal_env.client.service_client.config.target_host) as client:
        response = await client.post(
            "/ingest/commit",
            json=_body(f"test-{project_id}", diff="y" * (settings_limit + 1)),
            headers=HEADERS,
        )

    async with session_factory() as session:
        stored = await session.get(ChangeModel, UUID(response.json()["change_id"]))
    assert stored is not None
    assert stored.diff_truncated is True and len(stored.diff) == settings_limit
