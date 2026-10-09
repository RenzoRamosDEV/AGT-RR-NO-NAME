"""Raíz de composición: único sitio que conoce a la vez entrypoints, adapters y workflows
(son capas hermanas y no pueden importarse entre sí). Construye las dependencias reales."""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI
from sqlalchemy import text

from duelo.adapters.orchestration.temporal_client import LazyTemporalClient
from duelo.adapters.orchestration.temporal_review_starter import TemporalReviewStarter
from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.db import create_engine, create_session_factory
from duelo.adapters.persistence.event_repository import SqlAlchemyChangeEventRepository
from duelo.adapters.persistence.project_repository import SqlAlchemyProjectRepository
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application import queries
from duelo.application.ingest_commit import ChangeSubmission, IngestResult, ingest_commit, ingest_pr
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
from duelo.entrypoints.api.dependencies import ApiDependencies


def build_api_dependencies(settings: Settings) -> ApiDependencies:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    temporal = LazyTemporalClient(settings.temporal_address)
    starter = TemporalReviewStarter(temporal, settings.agent_names)

    projects = SqlAlchemyProjectRepository(session_factory)

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
            )

    async def get_change(change_id: UUID) -> ChangeDetail | None:
        async with session_factory() as session:
            return await queries.get_change_detail(
                SqlAlchemyChangeRepository(session),
                SqlAlchemyReviewRepository(session),
                change_id,
                expected_agents=expected_agents,
            )

    async def retry(change_id: UUID) -> Change:
        async with session_factory() as session:
            return await retry_review(
                SqlAlchemyChangeRepository(session),
                SqlAlchemyReviewRepository(session),
                starter,
                change_id,
                expected_agents=expected_agents,
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

    return ApiDependencies(
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
        close=engine.dispose,
    )


def create_app_from_env() -> FastAPI:
    """Factory para uvicorn (`--factory`): lee la configuración del entorno."""
    settings = Settings()  # type: ignore[call-arg]  # ingest_token viene del entorno
    return create_app(settings, build_api_dependencies(settings))
