"""Raíz de composición: único sitio que conoce a la vez entrypoints, adapters y workflows
(son capas hermanas y no pueden importarse entre sí). Construye las dependencias reales."""

from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy import text

from duelo.adapters.orchestration.temporal_client import LazyTemporalClient
from duelo.adapters.orchestration.temporal_review_starter import TemporalReviewStarter
from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.db import create_engine, create_session_factory
from duelo.adapters.persistence.project_repository import SqlAlchemyProjectRepository
from duelo.application.ingest_commit import CommitSubmission, ingest_commit
from duelo.config import Settings
from duelo.domain.change import Change
from duelo.entrypoints.api.app import create_app
from duelo.entrypoints.api.dependencies import ApiDependencies


def build_api_dependencies(settings: Settings) -> ApiDependencies:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    temporal = LazyTemporalClient(settings.temporal_address)
    starter = TemporalReviewStarter(temporal, settings.agent_names)

    async def ingest(submission: CommitSubmission) -> Change:
        async with session_factory() as session:
            return await ingest_commit(
                SqlAlchemyProjectRepository(session_factory),
                SqlAlchemyChangeRepository(session),
                starter,
                submission,
                max_diff_chars=settings.max_diff_chars,
            )

    async def check_postgres() -> None:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    return ApiDependencies(
        ingest_commit=ingest,
        readiness_checks={"postgres": check_postgres, "temporal": temporal.check_health},
        close=engine.dispose,
    )


def create_app_from_env() -> FastAPI:
    """Factory para uvicorn (`--factory`): lee la configuración del entorno."""
    settings = Settings()  # type: ignore[call-arg]  # ingest_token viene del entorno
    return create_app(settings, build_api_dependencies(settings))
