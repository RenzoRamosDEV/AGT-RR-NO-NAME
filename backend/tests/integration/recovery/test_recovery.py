"""Recuperación: comportamiento observable de Temporal + idempotencia, sin matar procesos.

(1) Sin worker de agentes el workflow espera y termina cuando aparece.
(2) Un fallo transitorio de persistencia se reintenta y deja una única review.
(3) Un acuse perdido tras confirmar (se escribe de verdad y luego falla) no duplica: la
    clave única absorbe el reintento. Es la semántica real de entrega *at-least-once*.
(4) Los reintentos están acotados: un fallo permanente acaba como fallo visible del workflow.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.client import WorkflowExecutionStatus, WorkflowFailureError
from temporalio.exceptions import ActivityError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from duelo.adapters.agents.fake import FakeAgent
from duelo.adapters.persistence.models import EventModel
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.domain.events import ReviewCompleted, ReviewFailed
from duelo.domain.review import Review
from duelo.workflows.dto import ReviewChangeInput
from duelo.workflows.review_change import ReviewChangeWorkflow
from tests.integration.helpers import make_activities, persist_change, reviews_for


@dataclass
class Flakiness:
    """Estado compartido entre las instancias del repositorio (una por intento)."""

    fail_times: int
    lose_ack: bool = False
    calls: int = 0


class FlakyReviewRepository:
    def __init__(self, inner: SqlAlchemyReviewRepository, flakiness: Flakiness) -> None:
        self._inner = inner
        self._flakiness = flakiness

    async def add(self, review: Review, event: ReviewCompleted | ReviewFailed) -> Review:
        state = self._flakiness
        state.calls += 1
        failing = state.calls <= state.fail_times
        if failing and not state.lose_ack:
            raise ConnectionError("la base de datos no responde")
        saved = await self._inner.add(review, event)
        if failing and state.lose_ack:
            raise ConnectionError("conexión perdida antes de recibir el acuse")
        return saved


def _flaky_factory(flakiness: Flakiness):
    return lambda session: FlakyReviewRepository(SqlAlchemyReviewRepository(session), flakiness)


async def _count_events(session_factory: async_sessionmaker, project_id, event_type: str) -> int:
    async with session_factory() as session:
        return (
            await session.execute(
                select(func.count())
                .select_from(EventModel)
                .where(EventModel.project_id == project_id, EventModel.type == event_type)
            )
        ).scalar_one()


async def _wait_for_pending_activities(handle: Any, expected: int, seconds: float = 15) -> None:
    """Espera (sin dormir a ciegas) a que Temporal tenga >= `expected` activities pendientes."""
    pending = 0
    for _ in range(int(seconds / 0.1)):
        description = await handle.describe()
        pending = len(description.raw_description.pending_activities)
        if pending >= expected:
            return
        await asyncio.sleep(0.1)
    raise AssertionError(
        f"esperaba >= {expected} activities pendientes, hay {pending}: "
        f"{description.raw_description}"
    )


async def _run_review_workflow(
    env: WorkflowEnvironment, activities: Any, change_id: str, agent_names: list[str]
) -> Any:
    async with (
        Worker(env.client, task_queue="platform", workflows=[ReviewChangeWorkflow]),
        Worker(env.client, task_queue="agents", activities=[activities.run_review]),
    ):
        return await env.client.execute_workflow(
            ReviewChangeWorkflow.run,
            ReviewChangeInput(change_id=change_id, agent_names=agent_names),
            id=f"review-{change_id}",
            task_queue="platform",
        )


async def test_workflow_waits_for_a_missing_agents_worker_and_finishes_when_it_appears(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await persist_change(session_factory, "a" * 40)
    agents = {"agent_1": FakeAgent("agent_1"), "agent_2": FakeAgent("agent_2")}
    activities = make_activities(session_factory, agents)

    async with Worker(temporal_env.client, task_queue="platform", workflows=[ReviewChangeWorkflow]):
        handle = await temporal_env.client.start_workflow(
            ReviewChangeWorkflow.run,
            ReviewChangeInput(change_id=str(change.id), agent_names=list(agents)),
            id=f"review-{change.id}",
            task_queue="platform",
        )

        # Las dos activities quedan pendientes: nadie atiende la cola `agents`.
        await _wait_for_pending_activities(handle, expected=2)
        assert (await handle.describe()).status == WorkflowExecutionStatus.RUNNING
        assert await reviews_for(session_factory, change) == []

        async with Worker(
            temporal_env.client, task_queue="agents", activities=[activities.run_review]
        ):
            results = await handle.result()

    assert {r.status for r in results} == {"completed"}
    assert len(await reviews_for(session_factory, change)) == 2


async def test_transient_persistence_failure_is_retried_and_leaves_a_single_review(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await persist_change(session_factory, "b" * 40)
    flakiness = Flakiness(fail_times=1)
    activities = make_activities(
        session_factory, {"agent_1": FakeAgent("agent_1")}, _flaky_factory(flakiness)
    )

    results = await _run_review_workflow(temporal_env, activities, str(change.id), ["agent_1"])

    assert [r.status for r in results] == ["completed"]
    assert flakiness.calls == 2
    assert len(await reviews_for(session_factory, change)) == 1
    assert await _count_events(session_factory, change.project_id, "review.completed") == 1


async def test_lost_ack_after_commit_does_not_duplicate_the_review_or_its_event(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await persist_change(session_factory, "c" * 40)
    flakiness = Flakiness(fail_times=1, lose_ack=True)
    activities = make_activities(
        session_factory, {"agent_1": FakeAgent("agent_1")}, _flaky_factory(flakiness)
    )

    results = await _run_review_workflow(temporal_env, activities, str(change.id), ["agent_1"])

    assert [r.status for r in results] == ["completed"]
    assert flakiness.calls == 2  # el primero se confirmó de verdad; el reintento lo absorbe
    assert len(await reviews_for(session_factory, change)) == 1
    assert await _count_events(session_factory, change.project_id, "review.completed") == 1


async def test_a_permanent_failure_exhausts_the_bounded_retries_and_fails_visibly(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await persist_change(session_factory, "d" * 40)
    flakiness = Flakiness(fail_times=10_000)
    activities = make_activities(
        session_factory, {"agent_1": FakeAgent("agent_1")}, _flaky_factory(flakiness)
    )

    with pytest.raises(WorkflowFailureError) as failure:
        await _run_review_workflow(temporal_env, activities, str(change.id), ["agent_1"])

    assert isinstance(failure.value.cause, ActivityError)
    assert flakiness.calls == 3  # RetryPolicy(maximum_attempts=3) del workflow
    assert await reviews_for(session_factory, change) == []
