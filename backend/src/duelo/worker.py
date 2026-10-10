"""Worker de desarrollo: un solo proceso para las task queues `platform` y `agents`.

Los agentes salen de `AGENT_NAMES`: `claude` y `codex` usan los CLI de esta máquina (con la sesión
que ya tengas iniciada, sin claves de API) y cualquier otro nombre es el agente de prueba. Debe
correr en tu máquina, donde esos CLI están autenticados; no en un contenedor.

    AGENT_NAMES=claude,codex uv run python -m duelo.worker

La API debe arrancarse con la misma `AGENT_NAMES`.
"""

from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from duelo.adapters.agents.registry import CliAgentConfig, build_agents, is_real_agent
from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.db import create_engine, create_session_factory
from duelo.adapters.persistence.project_repository import SqlAlchemyProjectRepository
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.config import WorkerSettings
from duelo.workflows.activities import ReviewActivities
from duelo.workflows.review_change import ReviewChangeWorkflow
from duelo.workflows.review_commit import ReviewCommitWorkflow


def cli_agent_config(settings: WorkerSettings) -> CliAgentConfig:
    return CliAgentConfig(
        timeout_seconds=settings.agent_timeout_seconds,
        max_concurrency=settings.agent_max_concurrency,
        claude_bin=settings.claude_bin,
        codex_bin=settings.codex_bin,
        claude_model=settings.claude_model,
        codex_model=settings.codex_model,
        claude_max_budget_usd=settings.claude_max_budget_usd,
    )


def build_workers(client: Client, settings: WorkerSettings) -> tuple[Worker, Worker]:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    activities = ReviewActivities(
        session_factory=session_factory,
        change_repository=SqlAlchemyChangeRepository,
        review_repository=SqlAlchemyReviewRepository,
        agents=build_agents(
            settings.agent_names,
            cli_agent_config(settings),
            SqlAlchemyProjectRepository(session_factory),
        ),
    )
    # Con CLI reales, los huecos de la queue `agents` se limitan a `AGENT_MAX_CONCURRENCY`: las
    # reviews sobrantes esperan en la cola de Temporal, donde no gastan el plazo de la activity,
    # en lugar de esperar dentro de ella. Solo con agentes de prueba no hay límite.
    real = any(is_real_agent(name) for name in settings.agent_names)
    return (
        Worker(
            client,
            task_queue="platform",
            workflows=[ReviewChangeWorkflow, ReviewCommitWorkflow],
        ),
        Worker(
            client,
            task_queue="agents",
            activities=[activities.run_review, activities.record_review_infrastructure_failure],
            max_concurrent_activities=settings.agent_max_concurrency if real else None,
        ),
    )


async def main() -> None:
    settings = WorkerSettings()
    client = await Client.connect(settings.temporal_address)
    platform, agents = build_workers(client, settings)
    async with platform, agents:
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
