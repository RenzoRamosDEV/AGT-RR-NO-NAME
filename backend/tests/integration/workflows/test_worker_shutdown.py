"""Apagado ordenado del worker de agentes con Temporal de test y Postgres real.

(1) Una review que no termina dentro del plazo de gracia se cancela, no deja rastro en la base de
    datos y la completa el siguiente worker, una sola vez.
(2) Una review que termina dentro del plazo se persiste y no se cancela.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.client import WorkflowHandle
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from duelo.adapters.agents.fake import FakeAgent
from duelo.application.task_queues import AGENTS_TASK_QUEUE, PLATFORM_TASK_QUEUE
from duelo.domain.change import Change
from duelo.domain.review import ReviewResult
from duelo.workflows.dto import ReviewChangeInput, RunReviewResult
from duelo.workflows.review_change import ReviewChangeWorkflow
from tests.integration.helpers import make_activities, persist_change, reviews_for

AGENT = "agent_slow"


class SlowAgent:
    """Agente que avisa cuando empieza, tarda `delay` segundos y recuerda si lo cancelaron."""

    name = AGENT

    def __init__(self, delay: float) -> None:
        self.started = asyncio.Event()
        self.cancelled = False
        self._delay = delay

    async def review(self, change: Change) -> ReviewResult:
        self.started.set()
        try:
            await asyncio.sleep(self._delay)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return ReviewResult(summary="lenta pero completa", score=6, findings=())


def _agents_worker(
    env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
    agent: object,
    grace: timedelta,
) -> Worker:
    return Worker(
        env.client,
        task_queue=AGENTS_TASK_QUEUE,
        activities=[make_activities(session_factory, {AGENT: agent}).run_review],
        graceful_shutdown_timeout=grace,
    )


async def _start_review(
    env: WorkflowEnvironment, change: Change
) -> WorkflowHandle[ReviewChangeWorkflow, list[RunReviewResult]]:
    return await env.client.start_workflow(
        ReviewChangeWorkflow.run,
        ReviewChangeInput(change_id=str(change.id), agent_names=[AGENT], run=1),
        id=f"shutdown-{uuid4()}",
        task_queue=PLATFORM_TASK_QUEUE,
    )


async def test_a_review_that_outlives_the_grace_is_cancelled_and_redone_once_by_the_next_worker(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await persist_change(session_factory, "a" * 40)
    slow = SlowAgent(delay=3600)

    async with Worker(
        temporal_env.client, task_queue=PLATFORM_TASK_QUEUE, workflows=[ReviewChangeWorkflow]
    ):
        handle = await _start_review(temporal_env, change)
        stopping = _agents_worker(
            temporal_env, session_factory, slow, grace=timedelta(milliseconds=200)
        )
        async with stopping:
            await asyncio.wait_for(slow.started.wait(), timeout=10)
        # Al salir del contexto el worker dejó de aceptar tareas, esperó 200 ms y canceló.

        assert slow.cancelled
        assert await reviews_for(session_factory, change) == []

        # El siguiente worker reintenta la activity y la review se persiste una sola vez.
        async with _agents_worker(
            temporal_env, session_factory, FakeAgent(AGENT), grace=timedelta(seconds=5)
        ):
            results = await handle.result()

    assert [r.status for r in results] == ["completed"]
    reviews = await reviews_for(session_factory, change)
    assert [(r.agent, r.status) for r in reviews] == [(AGENT, "completed")]


async def test_a_review_that_finishes_within_the_grace_is_persisted_and_not_cancelled(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await persist_change(session_factory, "b" * 40)
    quick = SlowAgent(delay=0.3)

    async with Worker(
        temporal_env.client, task_queue=PLATFORM_TASK_QUEUE, workflows=[ReviewChangeWorkflow]
    ):
        handle = await _start_review(temporal_env, change)
        async with _agents_worker(
            temporal_env, session_factory, quick, grace=timedelta(seconds=10)
        ):
            await asyncio.wait_for(quick.started.wait(), timeout=10)
        # El apagado esperó a que la review terminara en lugar de cancelarla.

        assert not quick.cancelled
        results = await handle.result()

    assert [r.status for r in results] == ["completed"]
    reviews = await reviews_for(session_factory, change)
    assert [(r.agent, r.status) for r in reviews] == [(AGENT, "completed")]
