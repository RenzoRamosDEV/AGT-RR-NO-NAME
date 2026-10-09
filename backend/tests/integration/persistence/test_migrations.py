"""El esquema de las migraciones debe coincidir con los modelos y ser reversible.

Cada módulo de test levanta su propio Postgres (fixture `database_url` con scope de
módulo), así que bajar a `base` aquí no afecta a otros tests.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

from duelo.adapters.persistence.models import Base
from duelo.domain.diff import summarize_diff

BACKEND_DIR = Path(__file__).resolve().parents[3]
EXPECTED_TABLES = {"projects", "changes", "events", "reviews"}


def _alembic() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


async def _tables(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        names = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    return names - {"alembic_version"}


@pytest.mark.regression
async def test_models_match_the_schema_produced_by_the_migrations(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        differences = await conn.run_sync(
            lambda sync_conn: compare_metadata(MigrationContext.configure(sync_conn), Base.metadata)
        )

    assert differences == []


async def test_migrations_are_reversible_upgrade_downgrade_upgrade(
    database_url: str, engine: AsyncEngine
) -> None:
    os.environ["DATABASE_URL"] = database_url
    assert await _tables(engine) == EXPECTED_TABLES

    # env.py usa asyncio.run: se ejecuta en un hilo, fuera del bucle del test
    await asyncio.to_thread(command.downgrade, _alembic(), "base")
    assert await _tables(engine) == set()

    await asyncio.to_thread(command.upgrade, _alembic(), "head")
    assert await _tables(engine) == EXPECTED_TABLES


_BACKFILL_DIFFS = [
    "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,2 +1,2 @@\n ctx\n-old\n+new\n",
    "diff --git a/x b/x\n@@ -1 +1 @@\n-- guiones\n+++ mas\n",
    "diff --git a/dir/f b/dir/f\nBinary files differ\n",
    "",
    "texto sin formato git",
    "".join(f"diff --git a/f{i} b/f{i}\n@@ -0,0 +1 @@\n+x\n" for i in range(210)),
]


async def test_the_diff_summary_migration_backfills_existing_changes_like_the_domain(
    database_url: str, engine: AsyncEngine
) -> None:
    """La migración lleva una copia congelada del algoritmo: debe coincidir con el dominio, y
    rellenar por lotes (hay más filas que el tamaño del lote)."""
    os.environ["DATABASE_URL"] = database_url
    await asyncio.to_thread(command.downgrade, _alembic(), "1f9758d504b6")
    project_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO projects (id, slug) VALUES (:id, :slug)"),
            {"id": project_id, "slug": f"mig-{project_id}"},
        )
        for i in range(105):
            diff = _BACKFILL_DIFFS[i % len(_BACKFILL_DIFFS)]
            await conn.execute(
                text(
                    "INSERT INTO changes (id, project_id, kind, ref, head_sha, title, author,"
                    " url, diff, diff_truncated, status, run)"
                    " VALUES (:id, :project_id, 'commit', 'r', :sha, 't', 'a', 'u', :diff,"
                    " false, 'pending', 1)"
                ),
                {"id": uuid4(), "project_id": project_id, "sha": f"{i:040d}", "diff": diff},
            )

    await asyncio.to_thread(command.upgrade, _alembic(), "head")

    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text("SELECT diff, diff_summary FROM changes WHERE project_id = :p"),
                {"p": project_id},
            )
        ).all()
    assert len(rows) == 105
    for diff, stored in rows:
        expected = summarize_diff(diff)
        assert stored["files_changed"] == expected.files_changed
        assert (stored["additions"], stored["deletions"]) == (
            expected.additions,
            expected.deletions,
        )
        assert stored["files"] == [
            {"path": f.path, "additions": f.additions, "deletions": f.deletions}
            for f in expected.files
        ]


async def test_migrations_leave_new_changes_with_an_empty_summary_by_default(
    engine: AsyncEngine,
) -> None:
    async with engine.connect() as conn:
        default = (
            await conn.execute(
                text(
                    "SELECT column_default FROM information_schema.columns"
                    " WHERE table_name = 'changes' AND column_name = 'diff_summary'"
                )
            )
        ).scalar_one()

    assert "files_changed" in default and "[]" in default


async def test_the_local_projects_migration_keeps_existing_projects_and_is_reversible(
    database_url: str, engine: AsyncEngine
) -> None:
    """Los proyectos anteriores (sin carpeta) quedan con path nulo y sin hooks; bajar quita las
    columnas sin perder los proyectos."""
    os.environ["DATABASE_URL"] = database_url
    await asyncio.to_thread(command.downgrade, _alembic(), "d4a8e1b5c602")
    project_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO projects (id, slug) VALUES (:id, :slug)"),
            {"id": project_id, "slug": f"old-{project_id}"},
        )
        columns = await conn.run_sync(
            lambda c: {col["name"] for col in inspect(c).get_columns("projects")}
        )
    assert columns == {"id", "slug"}

    await asyncio.to_thread(command.upgrade, _alembic(), "head")

    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT path, hooks_installed, github FROM projects WHERE id = :id"),
                {"id": project_id},
            )
        ).one()
        uniques = await conn.run_sync(
            lambda c: {
                tuple(u["column_names"]) for u in inspect(c).get_unique_constraints("projects")
            }
        )
    assert tuple(row) == (None, False, False)
    assert ("path",) in uniques and ("slug",) in uniques
