"""Commits deshechos y revertidos con Postgres real: la migración, las marcas atómicas e
idempotentes del barrido, el revert derivado de `reverts_sha`, la lectura sin consultas extra y la
integridad al borrar.

Cada módulo de test levanta su propio Postgres (fixture `database_url` con scope de módulo)."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import delete, event, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.commit_marks import SqlAlchemyCommitMarks
from duelo.adapters.persistence.event_repository import SqlAlchemyChangeEventRepository
from duelo.adapters.persistence.models import ChangeModel, EventModel
from duelo.application.ingest_change import ingest_change
from duelo.domain.change import Change, ChangeKind
from duelo.domain.commit_state import CommitState
from tests.integration.conftest import create_project

BACKEND_DIR = Path(__file__).resolve().parents[3]
BEFORE = "g7d5e9b3c126"
NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
SHA = [f"{n:040x}" for n in range(1, 12)]
NO_FILTER = {"kind": None, "status": None, "q": None, "expected_agents": 2}


def _alembic() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


async def _add(
    session_factory: async_sessionmaker,
    project_id: UUID,
    sha: str,
    *,
    kind: ChangeKind = ChangeKind.COMMIT,
    reverts: str | None = None,
) -> Change:
    async with session_factory() as session:
        return await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=project_id,
            kind=kind,
            ref="refs/heads/main",
            head_sha=sha,
            title=f"t {sha[-2:]}",
            author="a",
            url="https://example.com",
            diff="d",
            diff_truncated=False,
            reverts_sha=reverts,
        )


async def _row(session_factory: async_sessionmaker, change_id: UUID) -> ChangeModel:
    async with session_factory() as session:
        return (
            await session.execute(select(ChangeModel).where(ChangeModel.id == change_id))
        ).scalar_one()


async def _event_types(session_factory: async_sessionmaker, change: Change) -> list[str]:
    async with session_factory() as session:
        events = await SqlAlchemyChangeEventRepository(session).list_for_change(
            change.project_id, change.id
        )
    return [e.type for e in events]


async def _list(session_factory: async_sessionmaker, project_id: UUID, limit: int = 20):
    async with session_factory() as session:
        return await SqlAlchemyChangeRepository(session).list_for_project(
            project_id, limit=limit, after=None, **NO_FILTER
        )


async def _states(session_factory: async_sessionmaker, project_id: UUID):
    return {r.id: r for r in await _list(session_factory, project_id)}


async def _live_reverter(session_factory: async_sessionmaker, project_id: UUID, sha: str):
    async with session_factory() as session:
        return await SqlAlchemyChangeRepository(session).live_reverter(project_id, sha)


async def _discard(
    session_factory: async_sessionmaker, project_id: UUID, *changes: Change
) -> tuple[int, int]:
    return await SqlAlchemyCommitMarks(session_factory).apply(
        project_id, discard=[c.id for c in changes], restore=[], at=NOW
    )


async def _restore(
    session_factory: async_sessionmaker, project_id: UUID, *changes: Change
) -> tuple[int, int]:
    return await SqlAlchemyCommitMarks(session_factory).apply(
        project_id, discard=[], restore=[c.id for c in changes], at=NOW
    )


# --- migración --------------------------------------------------------------------------------


async def test_the_migration_keeps_existing_changes_active_and_is_reversible(
    database_url: str, engine: AsyncEngine
) -> None:
    """Los changes anteriores quedan sin marca (`active`); bajar quita las columnas y el índice sin
    perder ningún change."""
    os.environ["DATABASE_URL"] = database_url
    await asyncio.to_thread(command.downgrade, _alembic(), BEFORE)
    project_id, change_id = uuid4(), uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO projects (id, slug) VALUES (:id, :slug)"),
            {"id": project_id, "slug": f"old-{project_id}"},
        )
        await conn.execute(
            text(
                "INSERT INTO changes (id, project_id, kind, ref, head_sha, title, author, url,"
                " diff, diff_truncated, status, run, created_at)"
                " VALUES (:id, :p, 'commit', 'r', :sha, 't', 'a', 'u', 'd', false, 'pending', 1,"
                " now())"
            ),
            {"id": change_id, "p": project_id, "sha": "e" * 40},
        )
        columns = await conn.run_sync(
            lambda c: {col["name"] for col in inspect(c).get_columns("changes")}
        )
    assert "discarded_at" not in columns and "reverts_sha" not in columns

    await asyncio.to_thread(command.upgrade, _alembic(), "head")

    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT discarded_at, reverts_sha FROM changes WHERE id = :id"),
                {"id": change_id},
            )
        ).one()
        indexes = await conn.run_sync(
            lambda c: {i["name"] for i in inspect(c).get_indexes("changes")}
        )
    assert tuple(row) == (None, None)
    assert "ix_changes_project_reverts_sha" in indexes

    await asyncio.to_thread(command.downgrade, _alembic(), BEFORE)
    async with engine.connect() as conn:
        columns = await conn.run_sync(
            lambda c: {col["name"] for col in inspect(c).get_columns("changes")}
        )
        survivors = (
            await conn.execute(
                text("SELECT count(*) FROM changes WHERE id = :id"), {"id": change_id}
            )
        ).scalar_one()
    assert "discarded_at" not in columns and survivors == 1
    await asyncio.to_thread(command.upgrade, _alembic(), "head")


# --- marcas del barrido ------------------------------------------------------------------------


async def test_tracked_commits_are_only_the_commits_of_that_project(
    session_factory: async_sessionmaker,
) -> None:
    project, other = await create_project(session_factory), await create_project(session_factory)
    mine = await _add(session_factory, project, SHA[0])
    await _add(session_factory, project, SHA[1], kind=ChangeKind.PR)  # una PR no se rastrea
    await _add(session_factory, other, SHA[2])  # ni los commits de otro proyecto

    tracked = await SqlAlchemyCommitMarks(session_factory).tracked_commits(project)

    assert [(t.id, t.head_sha, t.discarded) for t in tracked] == [(mine.id, SHA[0], False)]


async def test_apply_marks_the_discarded_commits_with_their_event(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    lost = await _add(session_factory, project, SHA[0])
    kept = await _add(session_factory, project, SHA[1])

    result = await _discard(session_factory, project, lost)

    assert result == (1, 0)
    assert (await _row(session_factory, lost.id)).discarded_at == NOW
    assert (await _row(session_factory, kept.id)).discarded_at is None
    assert await _event_types(session_factory, lost) == ["change.created", "commit.discarded"]
    assert await _event_types(session_factory, kept) == ["change.created"]


async def test_apply_twice_marks_once_and_emits_one_event(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    lost = await _add(session_factory, project, SHA[0])
    marks = SqlAlchemyCommitMarks(session_factory)

    first = await marks.apply(project, discard=[lost.id], restore=[], at=NOW)
    second = await marks.apply(project, discard=[lost.id], restore=[], at=NOW + timedelta(hours=1))

    assert (first, second) == ((1, 0), (0, 0))
    assert (await _row(session_factory, lost.id)).discarded_at == NOW  # se conserva la primera
    assert await _event_types(session_factory, lost) == ["change.created", "commit.discarded"]


async def test_apply_restores_a_discarded_commit_with_its_event(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    change = await _add(session_factory, project, SHA[0])
    await _discard(session_factory, project, change)

    result = await _restore(session_factory, project, change)

    assert result == (0, 1)
    assert (await _row(session_factory, change.id)).discarded_at is None
    assert await _event_types(session_factory, change) == [
        "change.created",
        "commit.discarded",
        "commit.restored",
    ]


async def test_restoring_an_active_commit_does_nothing(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    change = await _add(session_factory, project, SHA[0])

    result = await _restore(session_factory, project, change)

    assert result == (0, 0)
    assert await _event_types(session_factory, change) == ["change.created"]


async def test_apply_ignores_prs_and_changes_of_other_projects(
    session_factory: async_sessionmaker,
) -> None:
    project, other = await create_project(session_factory), await create_project(session_factory)
    pr = await _add(session_factory, project, SHA[0], kind=ChangeKind.PR)
    foreign = await _add(session_factory, other, SHA[1])

    result = await _discard(session_factory, project, pr, foreign)

    assert result == (0, 0)
    assert (await _row(session_factory, pr.id)).discarded_at is None
    assert (await _row(session_factory, foreign.id)).discarded_at is None


async def test_two_simultaneous_sweeps_leave_one_mark_and_one_event(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    lost = await _add(session_factory, project, SHA[0])

    results = await asyncio.gather(*(_discard(session_factory, project, lost) for _ in range(6)))

    assert sorted(r[0] for r in results) == [0, 0, 0, 0, 0, 1]
    assert await _event_types(session_factory, lost) == ["change.created", "commit.discarded"]


# --- revert -----------------------------------------------------------------------------------


async def test_a_revert_commit_stores_the_sha_it_reverts(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    revert = await _add(session_factory, project, SHA[1], reverts=SHA[0])

    assert (await _row(session_factory, revert.id)).reverts_sha == SHA[0]


async def test_creating_the_revert_records_commit_reverted_on_the_original_once(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    original = await _add(session_factory, project, SHA[0])

    await _add(session_factory, project, SHA[1], reverts=SHA[0])
    await _add(session_factory, project, SHA[1], reverts=SHA[0])  # reenvío: no repite el evento

    assert await _event_types(session_factory, original) == ["change.created", "commit.reverted"]


async def test_a_revert_of_a_commit_that_is_not_there_is_stored_without_error_or_event(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)

    revert = await _add(session_factory, project, SHA[1], reverts=SHA[0])

    assert (await _row(session_factory, revert.id)).reverts_sha == SHA[0]
    assert await _event_types(session_factory, revert) == ["change.created"]


async def test_the_original_is_reverted_whichever_order_the_commits_arrive_in(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    revert = await _add(session_factory, project, SHA[1], reverts=SHA[0])

    original = await _add(session_factory, project, SHA[0])

    state = (await _states(session_factory, project))[original.id]
    assert state.commit_state is CommitState.REVERTED
    assert state.reverted_by is not None and state.reverted_by.id == revert.id


async def test_live_reverter_is_the_newest_revert_that_is_still_on_the_branch(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    await _add(session_factory, project, SHA[0])
    first = await _add(session_factory, project, SHA[1], reverts=SHA[0])
    second = await _add(session_factory, project, SHA[2], reverts=SHA[0])

    newest = await _live_reverter(session_factory, project, SHA[0])
    await _discard(session_factory, project, second)
    fallback = await _live_reverter(session_factory, project, SHA[0])
    await _discard(session_factory, project, first)
    none_left = await _live_reverter(session_factory, project, SHA[0])

    assert newest is not None and newest.id == second.id
    assert fallback is not None and (fallback.id, fallback.head_sha) == (first.id, SHA[1])
    assert none_left is None


async def test_live_reverter_only_looks_at_commits_of_the_same_project_and_never_at_itself(
    session_factory: async_sessionmaker,
) -> None:
    project, other = await create_project(session_factory), await create_project(session_factory)
    await _add(session_factory, project, SHA[0])
    await _add(session_factory, other, SHA[1], reverts=SHA[0])  # de otro proyecto
    await _add(session_factory, project, SHA[2], kind=ChangeKind.PR, reverts=SHA[0])  # una PR
    await _add(session_factory, project, SHA[0], kind=ChangeKind.PR)
    await _add(session_factory, project, SHA[3], reverts=SHA[3])  # se nombra a sí mismo

    assert await _live_reverter(session_factory, project, SHA[0]) is None
    assert await _live_reverter(session_factory, project, SHA[3]) is None


async def test_an_amended_revert_is_replaced_by_the_new_one_in_either_order(
    session_factory: async_sessionmaker,
) -> None:
    """La API ingiere el commit nuevo al instante y el barrido marca el antiguo cuando le toca."""
    project = await create_project(session_factory)
    original = await _add(session_factory, project, SHA[0])
    old = await _add(session_factory, project, SHA[1], reverts=SHA[0])

    new = await _add(session_factory, project, SHA[2], reverts=SHA[0])  # llega antes que la marca
    before = (await _states(session_factory, project))[original.id]
    await _discard(session_factory, project, old)
    after = (await _states(session_factory, project))[original.id]

    for state in (before, after):
        assert state.commit_state is CommitState.REVERTED
        assert state.reverted_by is not None and state.reverted_by.id == new.id


async def test_simultaneous_reverts_of_the_same_commit_need_no_coordination(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    original = await _add(session_factory, project, SHA[0])

    reverts = await asyncio.gather(
        *(_add(session_factory, project, SHA[n], reverts=SHA[0]) for n in range(1, 7))
    )

    state = (await _states(session_factory, project))[original.id]
    assert state.commit_state is CommitState.REVERTED
    assert state.reverted_by is not None and state.reverted_by.id in {r.id for r in reverts}


# --- lectura ----------------------------------------------------------------------------------


async def test_the_listing_gives_the_state_and_the_sha_of_the_reverting_commit(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    normal = await _add(session_factory, project, SHA[0])
    discarded = await _add(session_factory, project, SHA[1])
    reverted = await _add(session_factory, project, SHA[2])
    revert = await _add(session_factory, project, SHA[3], reverts=SHA[2])
    pr = await _add(session_factory, project, SHA[4], kind=ChangeKind.PR)
    await _discard(session_factory, project, discarded)

    rows = await _states(session_factory, project)

    assert rows[normal.id].commit_state is CommitState.ACTIVE
    assert rows[normal.id].reverted_by is None
    assert rows[discarded.id].commit_state is CommitState.DISCARDED
    assert rows[reverted.id].commit_state is CommitState.REVERTED
    assert rows[reverted.id].reverted_by is not None
    assert (rows[reverted.id].reverted_by.id, rows[reverted.id].reverted_by.head_sha) == (
        revert.id,
        SHA[3],
    )
    assert rows[revert.id].commit_state is CommitState.ACTIVE
    assert rows[pr.id].commit_state is CommitState.ACTIVE


async def test_discarded_wins_over_reverted_in_the_listing(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    original = await _add(session_factory, project, SHA[0])
    await _add(session_factory, project, SHA[1], reverts=SHA[0])
    await _discard(session_factory, project, original)

    state = (await _states(session_factory, project))[original.id]

    assert state.commit_state is CommitState.DISCARDED
    assert state.reverted_by is not None  # el dato del revert se conserva


async def test_an_undone_revert_leaves_the_original_active_until_it_comes_back(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    original = await _add(session_factory, project, SHA[0])
    revert = await _add(session_factory, project, SHA[1], reverts=SHA[0])

    await _discard(session_factory, project, revert)
    undone = (await _states(session_factory, project))[original.id]
    await _restore(session_factory, project, revert)
    back = (await _states(session_factory, project))[original.id]

    assert undone.commit_state is CommitState.ACTIVE and undone.reverted_by is None
    assert back.commit_state is CommitState.REVERTED and back.reverted_by is not None


async def test_the_listing_needs_no_extra_query_for_the_reverting_commit(
    engine: AsyncEngine, session_factory: async_sessionmaker
) -> None:
    """El SHA del revert sale de un LATERAL dentro de la misma consulta: listar commits revertidos
    cuesta lo mismo que listar commits normales (sin una consulta por fila)."""
    plain = await create_project(session_factory)
    with_reverts = await create_project(session_factory)
    for n in range(4):
        await _add(session_factory, plain, SHA[n])
    for n in range(4):
        await _add(session_factory, with_reverts, SHA[n])
    await _add(session_factory, with_reverts, SHA[5], reverts=SHA[0])
    await _add(session_factory, with_reverts, SHA[6], reverts=SHA[1])

    async def count_statements(project: UUID) -> int:
        statements: list[str] = []

        def capture(conn, cursor, statement, *args):  # type: ignore[no-untyped-def]
            statements.append(statement)

        event.listen(engine.sync_engine, "before_cursor_execute", capture)
        try:
            await _list(session_factory, project)
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", capture)
        return len(statements)

    assert await count_statements(plain) == await count_statements(with_reverts)


async def test_get_returns_the_discard_mark_and_the_reverts_sha(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    original = await _add(session_factory, project, SHA[0])
    revert = await _add(session_factory, project, SHA[1], reverts=SHA[0])
    await _discard(session_factory, project, original)

    async with session_factory() as session:
        repo = SqlAlchemyChangeRepository(session)
        stored_original = await repo.get(original.id)
        stored_revert = await repo.get(revert.id)

    assert stored_original is not None and stored_original.discarded_at == NOW
    assert stored_revert is not None and stored_revert.reverts_sha == SHA[0]


# --- integridad -------------------------------------------------------------------------------


async def test_deleting_the_reverting_commit_leaves_the_original_active(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    original = await _add(session_factory, project, SHA[0])
    revert = await _add(session_factory, project, SHA[1], reverts=SHA[0])

    async with session_factory() as session, session.begin():
        await session.execute(delete(ChangeModel).where(ChangeModel.id == revert.id))

    state = (await _states(session_factory, project))[original.id]
    assert state.commit_state is CommitState.ACTIVE


async def test_removing_a_project_deletes_every_change_and_event(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    original = await _add(session_factory, project, SHA[0])
    revert = await _add(session_factory, project, SHA[1], reverts=SHA[0])
    await _discard(session_factory, project, original)

    async with session_factory() as session, session.begin():
        await session.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project})

    async with session_factory() as session:
        left = (
            await session.execute(
                select(ChangeModel.id).where(ChangeModel.id.in_([original.id, revert.id]))
            )
        ).all()
        events = (
            await session.execute(select(EventModel.id).where(EventModel.project_id == project))
        ).all()
    assert left == [] and events == []
