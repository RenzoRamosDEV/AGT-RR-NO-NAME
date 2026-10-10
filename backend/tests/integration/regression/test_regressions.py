"""Un test por cada defecto ya corregido. Cada docstring dice de dónde viene.

Se ejecutan con `pytest -m regression`. Otros tests de regresión viven junto a su capa y
también llevan el marcador (agente desconocido en workflows, deriva modelo/migración,
NUL en eventos, estados estables en dominio).
"""

from __future__ import annotations

from dataclasses import fields

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.api.enums.v1 import EventType
from temporalio.client import WorkflowFailureError
from temporalio.converter import DataConverter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from duelo.adapters.agents.fake import FakeAgent
from duelo.application.task_queues import AGENTS_TASK_QUEUE, PLATFORM_TASK_QUEUE
from duelo.workflows.dto import ReviewChangeInput, RunReviewInput
from duelo.workflows.review_change import ReviewChangeWorkflow
from tests.integration.helpers import make_activities, persist_change, reviews_for

pytestmark = pytest.mark.regression


async def _run(
    env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
    change_id: str,
    agent_names: list[str],
    agents: dict[str, FakeAgent],
):
    activities = make_activities(session_factory, agents)
    async with (
        Worker(env.client, task_queue=PLATFORM_TASK_QUEUE, workflows=[ReviewChangeWorkflow]),
        Worker(
            env.client,
            task_queue=AGENTS_TASK_QUEUE,
            activities=[activities.run_review, activities.record_review_infrastructure_failure],
        ),
    ):
        handle = await env.client.start_workflow(
            ReviewChangeWorkflow.run,
            ReviewChangeInput(change_id=change_id, agent_names=agent_names),
            id=f"review-{change_id}",
            task_queue=PLATFORM_TASK_QUEUE,
        )
        try:
            result = await handle.result()
        except WorkflowFailureError:
            result = None
        return handle, result


async def test_regression_unknown_agent_is_attempted_exactly_once(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    """Ronda 9 de Codex: `self._agents[name]` lanzaba KeyError y Temporal reintentaba 3
    veces sin dejar ninguna Review. Ahora es un error no reintentable: un solo intento."""
    change = await persist_change(session_factory, "a" * 40)

    handle, result = await _run(
        temporal_env,
        session_factory,
        str(change.id),
        ["fantasma"],
        {"agent_1": FakeAgent("agent_1")},
    )

    history = await handle.fetch_history()
    started = [
        e for e in history.events if e.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_STARTED
    ]
    assert result is None
    assert len(started) == 1
    assert await reviews_for(session_factory, change) == []


async def test_regression_a_five_megabyte_diff_never_crosses_temporal(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    """Ronda 9 de Codex: el diff viajaba dentro de un ChangeDTO por el historial de Temporal
    (límite de 2 MB por payload). Con un diff de 5 MB el diseño antiguo habría fallado."""
    sentinel = "SENTINEL-DIFF-9f3c1a"
    change = await persist_change(session_factory, "b" * 40, diff=sentinel + "x" * 5_000_000)
    agents = {"agent_1": FakeAgent("agent_1"), "agent_2": FakeAgent("agent_2")}

    handle, result = await _run(
        temporal_env, session_factory, str(change.id), ["agent_1", "agent_2"], agents
    )

    assert result is not None and {r.status for r in result} == {"completed"}
    history = await handle.fetch_history()
    serialized = history.to_json()
    assert sentinel not in serialized  # el contenido del diff no viaja por Temporal
    assert len(serialized) < 50_000  # señal secundaria: el historial sigue siendo pequeño


async def test_regression_run_review_input_carries_only_ids_and_a_tiny_payload() -> None:
    """Misma causa que el anterior, comprobado sin servidor: el payload de la activity."""
    names = {f.name for f in fields(RunReviewInput)}
    payload = DataConverter.default.payload_converter.to_payload(
        RunReviewInput(change_id="id", agent_name="agent_1", run=1)
    )

    assert names == {"change_id", "agent_name", "run"}
    assert len(payload.data) < 200


async def test_regression_stored_status_values_are_the_stable_strings(
    session_factory: async_sessionmaker,
) -> None:
    """Pasar `status` a enums de dominio no debe cambiar lo guardado: los valores en la tabla
    siguen siendo 'pending', 'completed' y 'failed' (sin migración)."""
    from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
    from duelo.application.record_review import (
        record_review_failure,
        record_review_success,
    )
    from duelo.domain.review import ReviewResult

    change = await persist_change(session_factory, "c" * 40)
    async with session_factory() as session:
        await record_review_success(
            SqlAlchemyReviewRepository(session),
            change=change,
            agent="agent_1",
            run=1,
            result=ReviewResult("ok", 1, ()),
            raw_output=None,
            duration_ms=1,
        )
    async with session_factory() as session:
        await record_review_failure(
            SqlAlchemyReviewRepository(session), change=change, agent="agent_2", run=1, error="x"
        )

    async with session_factory() as session:
        change_status = (
            await session.execute(
                text("SELECT status FROM changes WHERE id = :id"), {"id": change.id}
            )
        ).scalar_one()
        review_statuses = set(
            (
                await session.execute(
                    text("SELECT status FROM reviews WHERE change_id = :id"), {"id": change.id}
                )
            )
            .scalars()
            .all()
        )

    assert change_status == "pending"
    assert review_statuses == {"completed", "failed"}
