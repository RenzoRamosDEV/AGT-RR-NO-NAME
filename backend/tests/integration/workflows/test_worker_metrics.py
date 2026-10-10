"""Con `TEMPORAL_METRICS_ADDRESS` el worker expone las métricas del SDK en Prometheus."""

from __future__ import annotations

import socket
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.client import Client
from temporalio.runtime import Runtime
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from duelo.adapters.agents.fake import FakeAgent
from duelo.application.task_queues import AGENTS_TASK_QUEUE, PLATFORM_TASK_QUEUE
from duelo.config import WorkerSettings
from duelo.worker import build_runtime
from duelo.workflows.dto import ReviewChangeInput
from duelo.workflows.review_change import ReviewChangeWorkflow
from tests.integration.helpers import make_activities, persist_change

AGENT = "agent_1"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _runtime_on_a_free_port() -> tuple[str, Runtime]:
    """`PrometheusConfig` no admite puerto 0: se elige uno libre y, si otro proceso lo ocupa
    entre la elección y el `bind` (carrera), se prueba con otro."""
    last_error: Exception | None = None
    for _ in range(5):
        address = f"127.0.0.1:{_free_port()}"
        try:
            runtime = build_runtime(WorkerSettings(temporal_metrics_address=address))
        except Exception as error:  # noqa: BLE001 - el SDK no tipa el fallo del bind
            last_error = error
            continue
        assert runtime is not None
        return address, runtime
    raise AssertionError(f"no se pudo abrir un puerto de métricas: {last_error}")


async def test_the_worker_exposes_sdk_metrics_in_prometheus_format(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    address, runtime = _runtime_on_a_free_port()

    # Un cliente propio con ese runtime: las métricas se registran en el runtime del worker.
    client = await Client.connect(
        temporal_env.client.service_client.config.target_host,
        namespace=temporal_env.client.namespace,
        runtime=runtime,
    )
    change = await persist_change(session_factory, "c" * 40)
    activities = make_activities(session_factory, {AGENT: FakeAgent(AGENT)})

    async with (
        Worker(client, task_queue=PLATFORM_TASK_QUEUE, workflows=[ReviewChangeWorkflow]),
        Worker(client, task_queue=AGENTS_TASK_QUEUE, activities=[activities.run_review]),
    ):
        await client.execute_workflow(
            ReviewChangeWorkflow.run,
            ReviewChangeInput(change_id=str(change.id), agent_names=[AGENT], run=1),
            id=f"metrics-{uuid4()}",
            task_queue=PLATFORM_TASK_QUEUE,
        )
        async with httpx.AsyncClient() as http:
            response = await http.get(f"http://{address}/metrics")

    assert response.status_code == 200
    body = response.text
    # Nombres reales del SDK (la doc oficial habla de «activity task schedule-to-start»).
    assert "temporal_workflow_task_schedule_to_start_latency" in body
    assert "temporal_activity_schedule_to_start_latency" in body
    assert "temporal_worker_task_slots_available" in body
    assert "temporal_request_failure" in body
