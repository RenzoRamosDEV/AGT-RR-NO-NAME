"""Fallo de infraestructura: `run_review` agota sus reintentos (Temporal de test, Postgres real).
El workflow debe registrar la review fallida en vez de dejar el change sin rastro."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

from duelo.adapters.agents.fake import FakeAgent
from duelo.adapters.persistence.models import EventModel
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application.task_queues import AGENTS_TASK_QUEUE, PLATFORM_TASK_QUEUE
from duelo.domain.change import Change
from duelo.domain.review_status import (
    RETRYABLE_STATUSES,
    review_status_from_counts,
)
from duelo.workflows.activities import INFRASTRUCTURE_FAILURE_MESSAGE
from duelo.workflows.dto import ReviewChangeInput, RunReviewInput
from duelo.workflows.review_change import COMPENSATE_PATCH, ReviewChangeWorkflow
from tests.integration.helpers import make_activities, persist_change, reviews_for
from tests.integration.workflows.legacy_review_change import ReviewChangeWorkflowBeforeCompensation

BOTH_AGENTS = ["agent_1", "agent_2"]


def _flaky(*broken: str) -> type[SqlAlchemyReviewRepository]:
    """Repositorio cuya base de datos «falla» al guardar el resultado de los agentes rotos, pero
    deja guardar la compensación (la reconoce por su mensaje genérico)."""

    class Flaky(SqlAlchemyReviewRepository):
        attempts: list[str] = []

        async def add(self, review, event):  # type: ignore[no-untyped-def]
            if review.agent in broken and review.error != INFRASTRUCTURE_FAILURE_MESSAGE:
                type(self).attempts.append(review.agent)
                raise ConnectionError("password authentication failed for user duelo (10.0.0.5)")
            return await super().add(review, event)

    return Flaky


async def _event_types(session_factory: async_sessionmaker, change: Change) -> list[str]:
    async with session_factory() as session:
        rows = await session.execute(
            select(EventModel.type).where(EventModel.payload["change_id"].astext == str(change.id))
        )
        return sorted(rows.scalars().all())


async def _run_review_change(
    env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
    change: Change,
    repository: type[SqlAlchemyReviewRepository],
):
    activities = make_activities(
        session_factory,
        {"agent_1": FakeAgent("agent_1"), "agent_2": FakeAgent("agent_2")},
        review_repository=repository,
    )
    async with (
        Worker(env.client, task_queue=PLATFORM_TASK_QUEUE, workflows=[ReviewChangeWorkflow]),
        Worker(
            env.client,
            task_queue=AGENTS_TASK_QUEUE,
            activities=[activities.run_review, activities.record_review_infrastructure_failure],
        ),
    ):
        workflow_id = f"review-{change.id}"
        results = await env.client.execute_workflow(
            ReviewChangeWorkflow.run,
            ReviewChangeInput(change_id=str(change.id), agent_names=BOTH_AGENTS),
            id=workflow_id,
            task_queue=PLATFORM_TASK_QUEUE,
        )
        history = await env.client.get_workflow_handle(workflow_id).fetch_history()
    return results, history


@pytest.mark.regression
async def test_an_agent_that_exhausts_its_retries_is_recorded_as_failed_and_the_other_completes(
    temporal_env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
) -> None:
    """Origen: si `run_review` agotaba sus 3 intentos por un fallo de infraestructura no se
    guardaba ninguna review; el change quedaba `pending`/`running` y no se podía reintentar."""
    change = await persist_change(session_factory, head_sha="1" * 40)
    repository = _flaky("agent_2")

    results, _ = await _run_review_change(temporal_env, session_factory, change, repository)

    assert {r.status for r in results} == {"completed", "failed"}
    stored = await reviews_for(session_factory, change)
    assert {(r.agent, r.status) for r in stored} == {
        ("agent_1", "completed"),
        ("agent_2", "failed"),
    }
    # Se reintentó 3 veces antes de compensar, y el mensaje guardado no arrastra la excepción.
    assert repository.attempts == ["agent_2"] * 3  # type: ignore[attr-defined]
    broken = next(r for r in stored if r.agent == "agent_2")
    assert broken.error == INFRASTRUCTURE_FAILURE_MESSAGE
    # Un solo `review.failed` y un solo `review.completed`: sin eventos duplicados.
    assert await _event_types(session_factory, change) == [
        "change.created",
        "review.completed",
        "review.failed",
    ]


async def test_every_agent_failing_leaves_the_change_failed_and_so_retryable(
    temporal_env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
) -> None:
    change = await persist_change(session_factory, head_sha="2" * 40)

    results, _ = await _run_review_change(
        temporal_env, session_factory, change, _flaky("agent_1", "agent_2")
    )

    assert {r.status for r in results} == {"failed"}
    stored = await reviews_for(session_factory, change)
    assert {(r.agent, r.status, r.run) for r in stored} == {
        ("agent_1", "failed", 1),
        ("agent_2", "failed", 1),
    }
    # Con todas las reviews registradas el estado agregado es `failed`, que sí es reintentable.
    status = review_status_from_counts(completed=0, failed=len(stored), expected_agents=2)
    assert status in RETRYABLE_STATUSES


async def test_the_compensation_is_recorded_in_the_history_under_a_patch_marker(
    temporal_env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
) -> None:
    """El cambio de comportamiento va bajo `workflow.patched`: queda un marcador en el historial
    para que las ejecuciones en vuelo anteriores se reproduzcan sin romperse."""
    change = await persist_change(session_factory, head_sha="3" * 40)

    _, history = await _run_review_change(temporal_env, session_factory, change, _flaky("agent_2"))

    markers = [e for e in history.events if e.HasField("marker_recorded_event_attributes")]
    assert any(COMPENSATE_PATCH in str(m.marker_recorded_event_attributes) for m in markers)


async def test_a_healthy_run_records_no_compensation_marker(
    temporal_env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
) -> None:
    """El parche solo se consulta cuando hay un `ActivityError`: un run sano no cambia."""
    change = await persist_change(session_factory, head_sha="5" * 40)

    results, history = await _run_review_change(
        temporal_env, session_factory, change, SqlAlchemyReviewRepository
    )

    assert {r.status for r in results} == {"completed"}
    markers = [e for e in history.events if e.HasField("marker_recorded_event_attributes")]
    assert not any(COMPENSATE_PATCH in str(m.marker_recorded_event_attributes) for m in markers)


async def test_repeating_the_compensation_does_not_duplicate_the_review_or_the_event(
    session_factory: async_sessionmaker,
) -> None:
    change = await persist_change(session_factory, head_sha="4" * 40)
    activities = make_activities(session_factory, {})
    review_input = RunReviewInput(change_id=str(change.id), agent_name="agent_2", run=1)

    first = await activities.record_review_infrastructure_failure(review_input)
    second = await activities.record_review_infrastructure_failure(review_input)

    assert first.review_id == second.review_id
    assert len(await reviews_for(session_factory, change)) == 1
    assert (await _event_types(session_factory, change)).count("review.failed") == 1


async def test_an_execution_recorded_before_the_compensation_still_replays(
    temporal_env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
) -> None:
    """Versionado: la historia de una ejecución anterior (que falló por infraestructura sin
    compensar) se reproduce con el workflow nuevo sin errores de no determinismo."""
    change = await persist_change(session_factory, head_sha="6" * 40)
    activities = make_activities(
        session_factory,
        {"agent_1": FakeAgent("agent_1"), "agent_2": FakeAgent("agent_2")},
        review_repository=_flaky("agent_2"),
    )
    workflow_id = f"review-{change.id}"
    async with (
        Worker(
            temporal_env.client,
            task_queue=PLATFORM_TASK_QUEUE,
            workflows=[ReviewChangeWorkflowBeforeCompensation],
        ),
        Worker(
            temporal_env.client, task_queue=AGENTS_TASK_QUEUE, activities=[activities.run_review]
        ),
    ):
        with pytest.raises(WorkflowFailureError):
            await temporal_env.client.execute_workflow(
                "ReviewChangeWorkflow",
                ReviewChangeInput(change_id=str(change.id), agent_names=BOTH_AGENTS),
                id=workflow_id,
                task_queue=PLATFORM_TASK_QUEUE,
            )
        history = await temporal_env.client.get_workflow_handle(workflow_id).fetch_history()

    await Replayer(workflows=[ReviewChangeWorkflow]).replay_workflow(history)
