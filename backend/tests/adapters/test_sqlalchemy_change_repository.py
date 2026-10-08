"""Test de integración con testcontainers (Postgres real). Fixtures en conftest.py."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from review_arena.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from review_arena.adapters.persistence.models import ChangeModel, EventModel
from review_arena.application.ingest_change import ingest_change
from review_arena.domain.change import Change, ChangeKind
from review_arena.domain.events import ChangeCreated
from tests.adapters.conftest import create_project


async def test_ingest_change_persists_change_and_event_atomically(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)

    async with session_factory() as session:
        change = await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=project_id,
            kind=ChangeKind.COMMIT,
            ref="refs/heads/main",
            head_sha="a" * 40,
            title="fix: algo",
            author="renzo",
            url="https://example.com/commit/a",
            diff="diff --git a/x b/x",
            diff_truncated=False,
        )

    async with session_factory() as session:
        stored = (
            await session.execute(select(ChangeModel).where(ChangeModel.id == change.id))
        ).scalar_one()
        events = (
            (await session.execute(select(EventModel).where(EventModel.project_id == project_id)))
            .scalars()
            .all()
        )

    assert stored.head_sha == "a" * 40
    assert len(events) == 1
    assert events[0].type == "change.created"


async def test_reingesting_same_natural_key_is_idempotent(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)

    async def _ingest() -> Change:
        async with session_factory() as session:
            return await ingest_change(
                SqlAlchemyChangeRepository(session),
                project_id=project_id,
                kind=ChangeKind.COMMIT,
                ref="refs/heads/main",
                head_sha="b" * 40,
                title="fix: algo",
                author="renzo",
                url="https://example.com/commit/b",
                diff="diff --git a/x b/x",
                diff_truncated=False,
            )

    first = await _ingest()
    second = await _ingest()

    assert first.id == second.id

    async with session_factory() as session:
        events = (
            (await session.execute(select(EventModel).where(EventModel.project_id == project_id)))
            .scalars()
            .all()
        )
    assert len(events) == 1


async def test_same_head_sha_in_different_projects_are_independent(
    session_factory: async_sessionmaker,
) -> None:
    head_sha = "d" * 40

    async def _ingest(project_id: UUID) -> Change:
        async with session_factory() as session:
            return await ingest_change(
                SqlAlchemyChangeRepository(session),
                project_id=project_id,
                kind=ChangeKind.COMMIT,
                ref="refs/heads/main",
                head_sha=head_sha,
                title="fix: algo",
                author="renzo",
                url="https://example.com/commit/d",
                diff="diff --git a/x b/x",
                diff_truncated=False,
            )

    project_a = await create_project(session_factory)
    project_b = await create_project(session_factory)

    first = await _ingest(project_a)
    second = await _ingest(project_b)

    assert first.id != second.id


async def test_rolls_back_change_if_event_write_fails(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    change = Change.new(
        project_id=project_id,
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha="e" * 40,
        title="fix: algo",
        author="renzo",
        url="https://example.com/commit/e",
        diff="diff --git a/x b/x",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )
    # project_id inexistente en el evento -> viola la FK de events.project_id,
    # forzando que la escritura del evento falle dentro de la misma transacción.
    broken_event = ChangeCreated(
        change_id=change.id,
        project_id=uuid4(),
        kind=change.kind.value,
        head_sha=change.head_sha,
    )

    async with session_factory() as session:
        with pytest.raises(Exception, match="(?i)foreign key"):
            await SqlAlchemyChangeRepository(session).add(change, broken_event)

    async with session_factory() as session:
        row = (
            await session.execute(select(ChangeModel).where(ChangeModel.id == change.id))
        ).scalar_one_or_none()
    assert row is None
