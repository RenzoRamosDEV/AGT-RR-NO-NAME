"""Escrituras simultáneas contra Postgres real.

El riesgo vive en la base de datos (`INSERT ... ON CONFLICT` bajo carrera), así que un fake
en memoria no demostraría nada. Se usan sesiones independientes (una por tarea) y se
comprueban invariantes finales en la BD, no tiempos.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.models import ChangeModel, EventModel, ReviewModel
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application.ingest_change import ingest_change
from duelo.application.record_review import record_review_success
from duelo.domain.change import Change, ChangeKind
from duelo.domain.review import ReviewResult
from tests.integration.conftest import create_project

PARALLEL = 10


async def _ingest(session_factory: async_sessionmaker, project_id: UUID, sha: str) -> Change:
    async with session_factory() as session:
        return await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=project_id,
            kind=ChangeKind.COMMIT,
            ref="refs/heads/main",
            head_sha=sha,
            title="fix: carrera",
            author="renzo",
            url="https://example.com/c",
            diff="diff --git a/x b/x",
            diff_truncated=False,
        )


async def _count(session_factory: async_sessionmaker, model, *where) -> int:
    async with session_factory() as session:
        return (
            await session.execute(select(func.count()).select_from(model).where(*where))
        ).scalar_one()


@pytest.mark.parametrize("round_number", range(5))
async def test_concurrent_ingests_of_the_same_key_create_one_change_and_one_event(
    session_factory: async_sessionmaker, round_number: int
) -> None:
    project_id = await create_project(session_factory)
    sha = f"{round_number:040d}"

    results = await asyncio.gather(
        *(_ingest(session_factory, project_id, sha) for _ in range(PARALLEL))
    )

    assert len({change.id for change in results}) == 1
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


async def test_concurrent_reviews_with_the_same_key_create_one_review_and_one_event(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    change = await _ingest(session_factory, project_id, "a" * 40)

    async def record() -> UUID:
        async with session_factory() as session:
            review = await record_review_success(
                SqlAlchemyReviewRepository(session),
                change=change,
                agent="agent_1",
                run=1,
                result=ReviewResult("ok", 5, ()),
                raw_output=None,
                duration_ms=1,
            )
            return review.id

    ids = await asyncio.gather(*(record() for _ in range(PARALLEL)))

    assert len(set(ids)) == 1
    assert await _count(session_factory, ReviewModel, ReviewModel.change_id == change.id) == 1
    assert (
        await _count(
            session_factory,
            EventModel,
            EventModel.project_id == project_id,
            EventModel.type == "review.completed",
        )
        == 1
    )


async def test_a_burst_of_distinct_keys_has_no_errors_and_one_row_per_key(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    keys = 30

    results = await asyncio.gather(
        *(_ingest(session_factory, project_id, f"{i:040d}") for i in range(keys))
    )

    assert len({change.id for change in results}) == keys
    assert await _count(session_factory, ChangeModel, ChangeModel.project_id == project_id) == keys
    assert await _count(session_factory, EventModel, EventModel.project_id == project_id) == keys


async def test_mixed_duplicates_and_distinct_keys_in_parallel(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    shas = [f"{i % 6:040d}" for i in range(24)]  # 6 claves distintas, cada una repetida 4 veces

    results = await asyncio.gather(*(_ingest(session_factory, project_id, sha) for sha in shas))

    by_sha: dict[str, set[UUID]] = {}
    for change in results:
        by_sha.setdefault(change.head_sha, set()).add(change.id)
    assert len(by_sha) == 6 and all(len(ids) == 1 for ids in by_sha.values())
    assert await _count(session_factory, ChangeModel, ChangeModel.project_id == project_id) == 6
    assert await _count(session_factory, EventModel, EventModel.project_id == project_id) == 6
