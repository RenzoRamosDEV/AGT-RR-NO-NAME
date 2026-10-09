"""Fixtures compartidos para los tests de integración con testcontainers (Postgres real).

Requiere Docker o Podman localmente. En Podman rootless hace falta además:
    export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
    export TESTCONTAINERS_RYUK_DISABLED=true
(Ryuk, el sidecar de limpieza de testcontainers, no funciona bien bajo Podman
rootless; en CI con Docker real no hace falta desactivarlo.)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from temporalio.testing import WorkflowEnvironment
from testcontainers.community.postgres import PostgresContainer

from review_arena.adapters.persistence.db import create_engine, create_session_factory
from review_arena.adapters.persistence.models import ProjectModel

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def database_url() -> AsyncIterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        url = postgres.get_connection_url()
        os.environ["DATABASE_URL"] = url
        alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
        yield url


@pytest.fixture
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    eng = create_engine(database_url)
    yield eng
    await eng.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return create_session_factory(engine)


async def create_project(session_factory: async_sessionmaker) -> UUID:
    project_id = uuid4()
    async with session_factory() as session, session.begin():
        await session.execute(insert(ProjectModel).values(id=project_id, slug=f"test-{project_id}"))
    return project_id


@pytest.fixture
async def temporal_env() -> AsyncIterator[WorkflowEnvironment]:
    """Servidor de test efímero de Temporal con salto de tiempo (sin Docker)."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        yield env
