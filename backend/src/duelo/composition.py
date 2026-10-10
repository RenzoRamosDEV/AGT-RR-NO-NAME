"""Raíz de composición: único sitio que conoce a la vez entrypoints, adapters y workflows
(son capas hermanas y no pueden importarse entre sí). Construye las dependencias reales."""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from sqlalchemy import text

from duelo.adapters.git.hook_installer import FileHookInstaller
from duelo.adapters.git.local_repository import LocalGitRepository
from duelo.adapters.github.gh_cli import GhPrSource
from duelo.adapters.orchestration.temporal_client import LazyTemporalClient
from duelo.adapters.orchestration.temporal_review_starter import TemporalReviewStarter
from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.db import create_engine, create_session_factory
from duelo.adapters.persistence.event_repository import SqlAlchemyChangeEventRepository
from duelo.adapters.persistence.project_repository import SqlAlchemyProjectRepository
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.adapters.ratelimit.in_memory import InMemoryRateLimiter
from duelo.application import queries
from duelo.application.ingest_commit import ChangeSubmission, IngestResult, ingest_commit, ingest_pr
from duelo.application.local_projects import (
    SyncResult,
    add_local_project,
    remove_local_project,
    sync_all_pull_requests,
    sync_pull_requests,
)
from duelo.application.read_models import (
    AgentStats,
    ChangeCursor,
    ChangeDetail,
    ChangeEvent,
    ChangePage,
    RawOutput,
)
from duelo.application.retry_review import retry_review
from duelo.config import Settings
from duelo.domain.change import Change, ChangeKind
from duelo.domain.project import Project
from duelo.domain.review_status import ChangeReviewStatus
from duelo.entrypoints.api.app import create_app
from duelo.entrypoints.api.background import periodic
from duelo.entrypoints.api.dependencies import ApiDependencies
from duelo.entrypoints.api.middleware import configure_access_logging
from duelo.entrypoints.hook import default_env_path


def build_api_dependencies(settings: Settings) -> ApiDependencies:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    temporal = LazyTemporalClient(settings.temporal_address)

    projects = SqlAlchemyProjectRepository(session_factory)
    starter = TemporalReviewStarter(temporal, settings.agent_names, projects)

    async def ingest(submission: ChangeSubmission) -> IngestResult:
        async with session_factory() as session:
            return await ingest_commit(
                projects,
                SqlAlchemyChangeRepository(session),
                starter,
                submission,
                max_diff_chars=settings.max_diff_chars,
            )

    async def ingest_pull_request(submission: ChangeSubmission) -> IngestResult:
        async with session_factory() as session:
            return await ingest_pr(
                projects,
                SqlAlchemyChangeRepository(session),
                starter,
                submission,
                max_diff_chars=settings.max_diff_chars,
            )

    # Cada lectura abre y cierra su propia sesión: ninguna deja transacciones abiertas.
    async def list_projects() -> list[Project]:
        return await queries.list_projects(projects)

    expected_agents = len(settings.agent_names)
    stale_after = timedelta(seconds=settings.stale_after_seconds)

    async def list_changes(
        slug: str,
        kind: ChangeKind | None,
        status: frozenset[ChangeReviewStatus] | None,
        q: str | None,
        limit: int,
        after: ChangeCursor | None,
    ) -> ChangePage:
        async with session_factory() as session:
            return await queries.list_changes(
                projects,
                SqlAlchemyChangeRepository(session),
                slug=slug,
                kind=kind,
                status=status,
                q=q,
                expected_agents=expected_agents,
                limit=limit,
                after=after,
                now=datetime.now(UTC),
                stale_after=stale_after,
            )

    async def get_change(change_id: UUID) -> ChangeDetail | None:
        async with session_factory() as session:
            return await queries.get_change_detail(
                SqlAlchemyChangeRepository(session),
                SqlAlchemyReviewRepository(session),
                change_id,
                expected_agents=expected_agents,
                now=datetime.now(UTC),
                stale_after=stale_after,
            )

    async def retry(change_id: UUID) -> Change:
        async with session_factory() as session:
            return await retry_review(
                SqlAlchemyChangeRepository(session),
                SqlAlchemyReviewRepository(session),
                starter,
                change_id,
                expected_agents=expected_agents,
                now=datetime.now(UTC),
            )

    async def agent_stats(project: str | None) -> list[AgentStats]:
        async with session_factory() as session:
            return await queries.agent_stats(
                projects, SqlAlchemyReviewRepository(session), project=project
            )

    async def list_change_events(change_id: UUID) -> list[ChangeEvent] | None:
        async with session_factory() as session:
            return await queries.change_events(
                SqlAlchemyChangeRepository(session),
                SqlAlchemyChangeEventRepository(session),
                change_id,
            )

    async def get_review_raw_output(review_id: UUID) -> RawOutput | None:
        async with session_factory() as session:
            return await queries.review_raw_output(SqlAlchemyReviewRepository(session), review_id)

    async def check_postgres() -> None:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    rate_limiter = (
        InMemoryRateLimiter(
            limit=settings.rate_limit_requests, window_seconds=settings.rate_limit_window_seconds
        )
        if settings.rate_limit_requests > 0
        else None
    )

    local = (
        _local_projects_wiring(settings, projects, ingest_pull_request)
        if settings.local_projects_enabled
        else None
    )

    return ApiDependencies(
        add_local_project=local.add if local else None,
        remove_project=local.remove if local else None,
        sync_pull_requests=local.sync if local else None,
        background_jobs=local.jobs if local else (),
        ingest_commit=ingest,
        ingest_pr=ingest_pull_request,
        list_projects=list_projects,
        list_changes=list_changes,
        get_change=get_change,
        retry_review=retry,
        agent_stats=agent_stats,
        list_change_events=list_change_events,
        get_review_raw_output=get_review_raw_output,
        readiness_checks={"postgres": check_postgres, "temporal": temporal.check_health},
        agent_names=tuple(settings.agent_names),
        close=engine.dispose,
        rate_limiter=rate_limiter,
    )


@dataclass(frozen=True)
class _LocalProjects:
    add: Callable[[str], Awaitable[Project]]
    remove: Callable[[str], Awaitable[None]]
    sync: Callable[[str], Awaitable[SyncResult]]
    jobs: list[Callable[[], Coroutine[Any, Any, None]]]


def _local_projects_wiring(
    settings: Settings,
    projects: SqlAlchemyProjectRepository,
    ingest_pull_request: Callable[[ChangeSubmission], Awaitable[IngestResult]],
) -> _LocalProjects:
    git = LocalGitRepository()
    hooks = FileHookInstaller(
        # El intérprete que corre la API es el que tiene `duelo` instalado: los hooks lo reusan.
        python=sys.executable,
        ingest_url=settings.ingest_url,
        ingest_token=settings.ingest_token,
        env_path=Path(settings.hook_env_path) if settings.hook_env_path else default_env_path(),
    )
    github = GhPrSource()

    async def add(path: str) -> Project:
        return await add_local_project(git, hooks, projects, path)

    async def remove(slug: str) -> None:
        await remove_local_project(hooks, projects, projects, slug)

    async def sync(slug: str) -> SyncResult:
        return await sync_pull_requests(projects, github, ingest_pull_request, slug)

    async def sync_all() -> None:
        await sync_all_pull_requests(projects, sync)

    jobs: list[Callable[[], Coroutine[Any, Any, None]]] = []
    if settings.pr_sync_interval_seconds > 0:
        interval = settings.pr_sync_interval_seconds
        jobs.append(lambda: periodic(interval, sync_all))
    return _LocalProjects(add=add, remove=remove, sync=sync, jobs=jobs)


def create_app_from_env() -> FastAPI:
    """Factory para uvicorn (`--factory`): lee la configuración del entorno."""
    settings = Settings()  # type: ignore[call-arg]  # ingest_token viene del entorno
    configure_access_logging()
    return create_app(settings, build_api_dependencies(settings))
