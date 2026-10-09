"""El esquema de las migraciones debe coincidir con los modelos y ser reversible.

Cada módulo de test levanta su propio Postgres (fixture `database_url` con scope de
módulo), así que bajar a `base` aquí no afecta a otros tests.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine

from review_arena.adapters.persistence.models import Base

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
