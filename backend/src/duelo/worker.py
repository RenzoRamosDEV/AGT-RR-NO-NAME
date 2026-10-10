"""Worker de desarrollo: un solo proceso para las task queues `platform` y `agents`.

Los agentes salen de `AGENT_NAMES`: `claude` y `codex` usan los CLI de esta máquina (con la sesión
que ya tengas iniciada, sin claves de API) y cualquier otro nombre es el agente de prueba. Debe
correr en tu máquina, donde esos CLI están autenticados; no en un contenedor.

    AGENT_NAMES=claude,codex uv run python -m duelo.worker

La API debe arrancarse con la misma `AGENT_NAMES` y el mismo `TEMPORAL_NAMESPACE`.

Operación: `SIGTERM` o `SIGINT` (Ctrl-C) paran el worker de forma ordenada: deja de aceptar tareas,
espera `WORKER_SHUTDOWN_GRACE_SECONDS` a las activities en curso y cancela las que sigan (el CLI del
agente se mata; Temporal reintenta esa review cuando vuelva un worker). Con
`TEMPORAL_METRICS_ADDRESS=host:puerto` expone las métricas del SDK en `/metrics` (Prometheus).
"""

from __future__ import annotations

import asyncio
import signal
from collections.abc import Sequence
from datetime import timedelta
from typing import Protocol

from temporalio.client import Client
from temporalio.runtime import PrometheusConfig, Runtime, TelemetryConfig
from temporalio.worker import Worker

from duelo.adapters.agents.registry import CliAgentConfig, build_agents, is_real_agent
from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.db import create_engine, create_session_factory
from duelo.adapters.persistence.project_repository import SqlAlchemyProjectRepository
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application.task_queues import AGENTS_TASK_QUEUE, PLATFORM_TASK_QUEUE
from duelo.config import WorkerSettings
from duelo.workflows.activities import ReviewActivities
from duelo.workflows.review_change import ReviewChangeWorkflow
from duelo.workflows.review_commit import ReviewCommitWorkflow

STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM)


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


def build_runtime(settings: WorkerSettings) -> Runtime | None:
    """`Runtime` del SDK con las métricas en Prometheus, solo si se pidió una dirección: un
    `Runtime` con telemetría abre un puerto, y sin la variable el worker no debe abrir ninguno."""
    if not settings.temporal_metrics_address:
        return None
    return Runtime(
        telemetry=TelemetryConfig(
            metrics=PrometheusConfig(bind_address=settings.temporal_metrics_address)
        )
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
    # Al apagar, las activities en curso tienen este plazo para terminar antes de cancelarse.
    grace = timedelta(seconds=settings.worker_shutdown_grace_seconds)
    return (
        Worker(
            client,
            task_queue=PLATFORM_TASK_QUEUE,
            workflows=[ReviewChangeWorkflow, ReviewCommitWorkflow],
            graceful_shutdown_timeout=grace,
        ),
        Worker(
            client,
            task_queue=AGENTS_TASK_QUEUE,
            activities=[activities.run_review, activities.record_review_infrastructure_failure],
            max_concurrent_activities=settings.agent_max_concurrency if real else None,
            graceful_shutdown_timeout=grace,
        ),
    )


def install_stop_signals(loop: asyncio.AbstractEventLoop, stop: asyncio.Event) -> None:
    """`SIGINT`/`SIGTERM` piden parar en vez de matar el proceso. Donde el bucle no admite
    manejadores de señal (Windows) no se instala nada y el worker se para como antes."""
    for sig in STOP_SIGNALS:
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            return


class Stoppable(Protocol):
    """Lo que `run_until_stopped` necesita de un `Worker` (y lo que imitan los tests)."""

    async def run(self) -> None: ...

    async def shutdown(self) -> None: ...


async def run_until_stopped(workers: Sequence[Stoppable], stop: asyncio.Event) -> None:
    """Mantiene los workers arriba hasta que `stop` se active y entonces los para **a la vez**:
    si se cerraran uno tras otro, el de `platform` seguiría aceptando workflow tasks (y
    programando activities) durante todo el plazo de gracia del de `agents`. Si un worker cae
    por su cuenta, se paran los demás y se propaga su error."""
    running = [asyncio.create_task(worker.run()) for worker in workers]
    stopping = asyncio.create_task(stop.wait())
    try:
        await asyncio.wait([stopping, *running], return_when=asyncio.FIRST_COMPLETED)
    finally:
        stopping.cancel()
        await asyncio.gather(*(worker.shutdown() for worker in workers))
        await asyncio.gather(*running)


async def main() -> None:
    settings = WorkerSettings()
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        runtime=build_runtime(settings),
    )
    stop = asyncio.Event()
    install_stop_signals(asyncio.get_running_loop(), stop)
    await run_until_stopped(build_workers(client, settings), stop)


if __name__ == "__main__":
    asyncio.run(main())
