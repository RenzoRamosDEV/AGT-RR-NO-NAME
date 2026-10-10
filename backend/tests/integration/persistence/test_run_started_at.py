"""`changes.run_started_at`: migración con backfill, persistencia y `advance_run` (Postgres real).

Cada módulo de test levanta su propio Postgres (fixture `database_url` con scope de módulo)."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.application.ingest_change import ingest_change
from duelo.domain.change import ChangeKind
from tests.integration.conftest import create_project

BACKEND_DIR = Path(__file__).resolve().parents[3]
BEFORE = "e5b9c2f1a703"
NOW = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)


def _alembic() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


async def _persist(session_factory: async_sessionmaker, sha: str):
    project_id = await create_project(session_factory)
    async with session_factory() as session:
        return await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=project_id,
            kind=ChangeKind.COMMIT,
            ref="refs/heads/main",
            head_sha=sha,
            title="t",
            author="a",
            url="https://example.com",
            diff="d",
            diff_truncated=False,
        )


async def test_the_migration_backfills_existing_changes_from_created_at_and_is_reversible(
    database_url: str, engine: AsyncEngine
) -> None:
    """Los changes anteriores no tienen otro dato que su creación: `run_started_at` la copia; bajar
    quita la columna sin perder los changes."""
    os.environ["DATABASE_URL"] = database_url
    await asyncio.to_thread(command.downgrade, _alembic(), BEFORE)
    project_id, change_id = uuid4(), uuid4()
    created = datetime(2025, 6, 1, 8, 30, tzinfo=UTC)
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO projects (id, slug) VALUES (:id, :slug)"),
            {"id": project_id, "slug": f"old-{project_id}"},
        )
        await conn.execute(
            text(
                "INSERT INTO changes (id, project_id, kind, ref, head_sha, title, author, url,"
                " diff, diff_truncated, status, run, created_at)"
                " VALUES (:id, :p, 'commit', 'r', :sha, 't', 'a', 'u', 'd', false, 'pending', 2,"
                " :created)"
            ),
            {"id": change_id, "p": project_id, "sha": "e" * 40, "created": created},
        )
        columns = await conn.run_sync(
            lambda c: {col["name"] for col in inspect(c).get_columns("changes")}
        )
    assert "run_started_at" not in columns

    await asyncio.to_thread(command.upgrade, _alembic(), "head")

    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT created_at, run_started_at, run FROM changes WHERE id = :id"),
                {"id": change_id},
            )
        ).one()
    assert row.run_started_at == row.created_at == created
    assert row.run == 2  # el resto de la fila no cambia

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
    assert "run_started_at" not in columns and survivors == 1
    await asyncio.to_thread(command.upgrade, _alembic(), "head")


async def test_a_new_change_starts_its_first_run_when_it_is_created(
    session_factory: async_sessionmaker,
) -> None:
    change = await _persist(session_factory, "1" * 40)

    async with session_factory() as session:
        stored = await SqlAlchemyChangeRepository(session).get(change.id)

    assert stored is not None
    assert stored.run_started_at == stored.created_at


async def test_advance_run_stores_the_start_of_the_new_run_and_keeps_the_creation(
    session_factory: async_sessionmaker,
) -> None:
    change = await _persist(session_factory, "2" * 40)
    started = NOW + timedelta(days=3)

    async with session_factory() as session:
        advanced = await SqlAlchemyChangeRepository(session).advance_run(
            change.id, from_run=1, started_at=started
        )

    assert advanced is not None
    assert (advanced.run, advanced.run_started_at) == (2, started)
    assert advanced.created_at == change.created_at
    async with session_factory() as session:
        stored = await SqlAlchemyChangeRepository(session).get(change.id)
    assert stored is not None and stored.run_started_at == started


async def test_a_lost_compare_and_swap_does_not_touch_the_clock(
    session_factory: async_sessionmaker,
) -> None:
    change = await _persist(session_factory, "3" * 40)
    async with session_factory() as session:
        await SqlAlchemyChangeRepository(session).advance_run(change.id, from_run=1, started_at=NOW)
    async with session_factory() as session:
        lost = await SqlAlchemyChangeRepository(session).advance_run(
            change.id, from_run=1, started_at=NOW + timedelta(days=9)
        )

    async with session_factory() as session:
        stored = await SqlAlchemyChangeRepository(session).get(change.id)
    assert lost is None
    assert stored is not None and (stored.run, stored.run_started_at) == (2, NOW)


async def test_the_channel_listing_carries_the_start_of_the_current_run(
    session_factory: async_sessionmaker,
) -> None:
    change = await _persist(session_factory, "4" * 40)
    started = NOW + timedelta(days=1)
    async with session_factory() as session:
        await SqlAlchemyChangeRepository(session).advance_run(
            change.id, from_run=1, started_at=started
        )

    async with session_factory() as session:
        (row,) = await SqlAlchemyChangeRepository(session).list_for_project(
            change.project_id,
            kind=None,
            status=None,
            q=None,
            expected_agents=2,
            limit=10,
            after=None,
        )

    assert row.run_started_at == started
    assert row.created_at == change.created_at
