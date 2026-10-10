"""Reutilización de las reviews de un commit en su PR idéntica (Postgres real).

Cada módulo de test levanta su propio Postgres (fixture `database_url` con scope de módulo)."""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.models import EventModel, ReviewModel
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application.ingest_change import ingest_change
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewReused
from duelo.domain.review import Finding, Review, ReviewResult
from tests.integration.conftest import create_project

BACKEND_DIR = Path(__file__).resolve().parents[3]
BEFORE = "f6c4d8a2b915"
AGENTS = ("claude", "codex")
SHA = "d" * 40
DIFF = "diff --git a/a.py b/a.py\n+x\n"
NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def _alembic() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


async def _ingest(
    session_factory: async_sessionmaker,
    project_id: UUID,
    kind: ChangeKind,
    *,
    diff: str = DIFF,
    sha: str = SHA,
    change_id: UUID | None = None,
) -> Change:
    async with session_factory() as session:
        return await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=project_id,
            kind=kind,
            ref="main",
            head_sha=sha,
            title="feat: algo",
            author="renzo",
            url="",
            diff=diff,
            diff_truncated=False,
            change_id=change_id,
            agent_names=AGENTS,
        )


async def _review(session_factory: async_sessionmaker, change: Change, agent: str) -> None:
    review = Review.succeeded(
        change_id=change.id,
        agent=agent,
        run=change.run,
        result=ReviewResult(
            summary=f"resumen de {agent}",
            score=9,
            findings=(Finding("bug", "a.py", 3, "falla"),),
        ),
        raw_output="cruda",
        duration_ms=1500,
        created_at=NOW,
    )
    async with session_factory() as session:
        await SqlAlchemyReviewRepository(session).add(
            review,
            ReviewCompleted(
                review_id=review.id, change_id=change.id, project_id=change.project_id, agent=agent
            ),
        )


async def _reviewed_commit(session_factory: async_sessionmaker, project_id: UUID) -> Change:
    commit = await _ingest(session_factory, project_id, ChangeKind.COMMIT)
    for agent in AGENTS:
        await _review(session_factory, commit, agent)
    return commit


async def _rows(session_factory: async_sessionmaker, change: Change) -> list[ReviewModel]:
    async with session_factory() as session:
        found = await session.execute(
            select(ReviewModel)
            .where(ReviewModel.change_id == change.id)
            .order_by(ReviewModel.agent)
        )
        return list(found.scalars())


async def _events(session_factory: async_sessionmaker, change: Change) -> list[str]:
    async with session_factory() as session:
        found = await session.execute(
            select(EventModel.type)
            .where(EventModel.payload["change_id"].astext == str(change.id))
            .order_by(EventModel.id)
        )
        return list(found.scalars())


async def test_a_pr_is_stored_with_the_reviews_copied_from_its_commit(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    commit = await _reviewed_commit(session_factory, project_id)

    pr = await _ingest(session_factory, project_id, ChangeKind.PR)

    copies = await _rows(session_factory, pr)
    assert [c.agent for c in copies] == list(AGENTS)
    for copy in copies:
        assert copy.reused_from_change_id == commit.id
        assert (copy.run, copy.status, copy.score, copy.duration_ms) == (1, "completed", 9, 1500)
        assert copy.summary == f"resumen de {copy.agent}"
        assert copy.findings == [{"severity": "bug", "file": "a.py", "line": 3, "message": "falla"}]
        assert copy.raw_output is None and copy.error is None
    assert await _events(session_factory, pr) == [
        "change.created",
        "review.reused",
        "review.reused",
    ]
    # El commit conserva las suyas, propias (sin marca).
    assert all(r.reused_from_change_id is None for r in await _rows(session_factory, commit))
    async with session_factory() as session:
        repo = SqlAlchemyChangeRepository(session)
        assert await repo.has_reused_reviews(pr.id)
        assert not await repo.has_reused_reviews(commit.id)


async def test_resending_the_pr_copies_and_records_nothing_more(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    await _reviewed_commit(session_factory, project_id)
    first = await _ingest(session_factory, project_id, ChangeKind.PR)

    again = await _ingest(session_factory, project_id, ChangeKind.PR, change_id=uuid4())

    assert again.id == first.id
    assert len(await _rows(session_factory, first)) == 2
    assert (await _events(session_factory, first)).count("review.reused") == 2


async def test_a_pr_with_a_different_diff_gets_no_copies(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    await _reviewed_commit(session_factory, project_id)

    pr = await _ingest(session_factory, project_id, ChangeKind.PR, diff=DIFF + "+otro\n")

    assert await _rows(session_factory, pr) == []
    async with session_factory() as session:
        assert not await SqlAlchemyChangeRepository(session).has_reused_reviews(pr.id)


async def test_simultaneous_ingestions_of_the_same_pr_leave_one_review_per_agent(
    session_factory: async_sessionmaker,
) -> None:
    """Origen: dos ingestas simultáneas de la misma PR (p. ej. un `push` y «Sincronizar PRs»)
    calculan las mismas copias; solo una puede insertarlas."""
    project_id = await create_project(session_factory)
    await _reviewed_commit(session_factory, project_id)
    candidates = [uuid4() for _ in range(6)]

    changes = await asyncio.gather(
        *(_ingest(session_factory, project_id, ChangeKind.PR, change_id=c) for c in candidates)
    )

    pr = changes[0]
    assert {c.id for c in changes} == {pr.id}  # todas devuelven el mismo change
    assert pr.id in candidates  # el de la ingesta que ganó la carrera
    assert [r.agent for r in await _rows(session_factory, pr)] == list(AGENTS)
    assert (await _events(session_factory, pr)).count("review.reused") == 2


async def test_a_failure_copying_a_review_leaves_no_change_behind(
    session_factory: async_sessionmaker,
) -> None:
    """La PR nace con todas las reviews copiadas o no nace: si falla una inserción, el change y su
    evento se deshacen (misma transacción)."""
    project_id = await create_project(session_factory)
    commit = await _reviewed_commit(session_factory, project_id)
    pr = Change.new(
        project_id=project_id,
        kind=ChangeKind.PR,
        ref="main",
        head_sha=SHA,
        title="t",
        author="a",
        url="",
        diff=DIFF,
        diff_truncated=False,
        created_at=NOW,
    )
    source = [
        Review.reused_from(
            Review.succeeded(
                change_id=commit.id,
                agent=agent,
                run=1,
                result=ReviewResult(summary="s", score=1),
                raw_output=None,
                duration_ms=1,
                created_at=NOW,
            ),
            change_id=pr.id,
            created_at=NOW,
        )
        for agent in AGENTS
    ]
    first, second = source
    # Misma clave primaria que la primera: la segunda inserción viola la PK y tumba la transacción.
    pairs = [
        (r, ReviewReused.of(r, project_id=project_id))
        for r in (first, replace(second, id=first.id))
    ]

    async with session_factory() as session:
        with pytest.raises(IntegrityError):
            await SqlAlchemyChangeRepository(session).add(
                pr, ChangeCreated(pr.id, project_id, "pr", SHA), pairs
            )

    async with session_factory() as session:
        assert await SqlAlchemyChangeRepository(session).get(pr.id) is None
    assert await _events(session_factory, pr) == []


async def test_deleting_the_source_commit_keeps_the_pr_reviews_and_clears_the_mark(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    commit = await _reviewed_commit(session_factory, project_id)
    pr = await _ingest(session_factory, project_id, ChangeKind.PR)

    async with session_factory() as session, session.begin():
        await session.execute(text("DELETE FROM changes WHERE id = :id"), {"id": commit.id})

    copies = await _rows(session_factory, pr)
    assert len(copies) == 2
    assert all(c.reused_from_change_id is None for c in copies)


async def test_the_source_lookup_returns_only_the_current_run_of_the_commit(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    commit = await _reviewed_commit(session_factory, project_id)

    async with session_factory() as session:
        repo = SqlAlchemyChangeRepository(session)
        found = await repo.find_commit_with_reviews(project_id, SHA)
        assert found is not None and found.change.id == commit.id
        assert sorted(r.agent for r in found.reviews) == list(AGENTS)
        assert await repo.find_commit_with_reviews(project_id, "0" * 40) is None
        await repo.advance_run(commit.id, from_run=1, started_at=NOW)

    async with session_factory() as session:
        retried = await SqlAlchemyChangeRepository(session).find_commit_with_reviews(
            project_id, SHA
        )
    assert retried is not None and retried.change.run == 2 and retried.reviews == ()


async def test_the_channel_listing_marks_the_reused_reviews(
    session_factory: async_sessionmaker,
) -> None:
    project_id = await create_project(session_factory)
    commit = await _reviewed_commit(session_factory, project_id)
    pr = await _ingest(session_factory, project_id, ChangeKind.PR)

    async with session_factory() as session:
        rows = await SqlAlchemyChangeRepository(session).list_for_project(
            project_id,
            kind=ChangeKind.PR,
            status=None,
            q=None,
            expected_agents=2,
            limit=10,
            after=None,
        )

    (item,) = rows
    assert item.id == pr.id and item.review_status.value == "completed"
    assert [b.reused_from for b in item.reviews] == [commit.id, commit.id]


async def test_the_migration_adds_the_nullable_column_and_is_reversible(
    database_url: str, engine: AsyncEngine
) -> None:
    """Las reviews anteriores quedan sin marca (propias); bajar quita la columna y el índice sin
    perder las reviews."""
    os.environ["DATABASE_URL"] = database_url
    await asyncio.to_thread(command.downgrade, _alembic(), BEFORE)
    project_id, change_id, review_id = uuid4(), uuid4(), uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO projects (id, slug) VALUES (:id, :slug)"),
            {"id": project_id, "slug": f"old-{project_id}"},
        )
        await conn.execute(
            text(
                "INSERT INTO changes (id, project_id, kind, ref, head_sha, title, author, url,"
                " diff, diff_truncated, status, run, created_at, run_started_at)"
                " VALUES (:id, :p, 'commit', 'r', :sha, 't', 'a', 'u', 'd', false, 'pending', 1,"
                " now(), now())"
            ),
            {"id": change_id, "p": project_id, "sha": "9" * 40},
        )
        await conn.execute(
            text(
                "INSERT INTO reviews (id, change_id, agent, run, status, findings, created_at)"
                " VALUES (:id, :c, 'claude', 1, 'completed', '[]'::jsonb, now())"
            ),
            {"id": review_id, "c": change_id},
        )
        columns = await conn.run_sync(
            lambda c: {col["name"] for col in inspect(c).get_columns("reviews")}
        )
    assert "reused_from_change_id" not in columns

    await asyncio.to_thread(command.upgrade, _alembic(), "head")

    async with engine.connect() as conn:
        mark = (
            await conn.execute(
                text("SELECT reused_from_change_id FROM reviews WHERE id = :id"), {"id": review_id}
            )
        ).scalar_one()
        indexes = await conn.run_sync(
            lambda c: {i["name"] for i in inspect(c).get_indexes("reviews")}
        )
        on_delete = (
            await conn.execute(
                text(
                    "SELECT confdeltype FROM pg_constraint WHERE conrelid = 'reviews'::regclass"
                    " AND confrelid = 'changes'::regclass AND conkey = ARRAY["
                    "(SELECT attnum FROM pg_attribute WHERE attrelid = 'reviews'::regclass"
                    " AND attname = 'reused_from_change_id')]"
                )
            )
        ).scalar_one()
    assert mark is None
    assert "ix_reviews_reused_from_change_id" in indexes
    assert bytes(on_delete) == b"n"  # ON DELETE SET NULL

    await asyncio.to_thread(command.downgrade, _alembic(), BEFORE)
    async with engine.connect() as conn:
        kept = (
            await conn.execute(
                text("SELECT count(*) FROM reviews WHERE id = :id"), {"id": review_id}
            )
        ).scalar_one()
        columns = await conn.run_sync(
            lambda c: {col["name"] for col in inspect(c).get_columns("reviews")}
        )
    assert kept == 1 and "reused_from_change_id" not in columns
    await asyncio.to_thread(command.upgrade, _alembic(), "head")
