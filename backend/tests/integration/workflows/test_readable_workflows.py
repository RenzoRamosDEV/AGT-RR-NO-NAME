"""Lo que se ve en Temporal: nombres legibles y la respuesta de cada reviewer.

Se comprueba sobre el historial real de las ejecuciones (lo mismo que enseña su interfaz): el
resultado de cada actividad, los resúmenes de usuario y los «Current Details» del hijo."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.api.enums.v1 import EventType
from temporalio.api.sdk.v1 import WorkflowMetadata
from temporalio.client import WorkflowHandle, WorkflowHistory
from temporalio.converter import DataConverter
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

from duelo.adapters.agents.fake import FakeAgent
from duelo.adapters.orchestration.temporal_client import LazyTemporalClient
from duelo.adapters.orchestration.temporal_review_starter import TemporalReviewStarter, workflow_id
from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.models import ProjectModel
from duelo.adapters.persistence.project_repository import SqlAlchemyProjectRepository
from duelo.application.ingest_change import ingest_change
from duelo.application.review_requests import ReviewCommitInput
from duelo.application.workflow_naming import child_workflow_id
from duelo.domain.change import Change, ChangeKind
from duelo.domain.review import Finding, ReviewResult
from duelo.workflows.review_change import ReviewChangeWorkflow
from duelo.workflows.review_commit import ReviewCommitWorkflow
from tests.integration.helpers import make_activities, reviews_for
from tests.integration.workflows.legacy_review_change import ReviewChangeWorkflowBeforeCompensation
from tests.integration.workflows.legacy_review_commit import ReviewCommitWorkflowBeforeReadableNames

SLUG = "acme/widgets"
AGENTS = ["agent_1", "agent_2"]
CONVERTER = DataConverter.default.payload_converter


async def _persist(
    session_factory: async_sessionmaker,
    *,
    sha: str,
    kind: ChangeKind = ChangeKind.COMMIT,
    title: str = "fix: algo",
) -> Change:
    async with session_factory() as session, session.begin():
        # La base de datos se comparte entre tests: el proyecto se crea una sola vez.
        await session.execute(
            insert(ProjectModel)
            .values(id=uuid4(), slug=SLUG)
            .on_conflict_do_nothing(index_elements=[ProjectModel.slug])
        )
        project_id = (
            await session.execute(select(ProjectModel.id).where(ProjectModel.slug == SLUG))
        ).scalar_one()
    async with session_factory() as session:
        return await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=project_id,
            kind=kind,
            ref="refs/heads/main",
            head_sha=sha,
            title=title,
            author="renzo",
            url="https://example.com/" + sha,
            diff="diff --git a/x b/x",
            diff_truncated=False,
        )


def _starter(env: WorkflowEnvironment, session_factory: async_sessionmaker):
    address = env.client.service_client.config.target_host
    return TemporalReviewStarter(
        LazyTemporalClient(address), AGENTS, SqlAlchemyProjectRepository(session_factory)
    )


def _workers(
    env: WorkflowEnvironment, session_factory: async_sessionmaker, agents: dict[str, FakeAgent]
):
    activities = make_activities(session_factory, agents)
    return (
        Worker(
            env.client,
            task_queue="platform",
            workflows=[ReviewChangeWorkflow, ReviewCommitWorkflow],
        ),
        Worker(
            env.client,
            task_queue="agents",
            activities=[activities.run_review, activities.record_review_infrastructure_failure],
        ),
    )


def _events(history: WorkflowHistory, event_type: EventType.ValueType) -> Iterator[Any]:
    return (event for event in history.events if event.event_type == event_type)


def _completed_activity_results(history: WorkflowHistory) -> list[dict[str, Any]]:
    return [
        CONVERTER.from_payload(event.activity_task_completed_event_attributes.result.payloads[0])
        for event in _events(history, EventType.EVENT_TYPE_ACTIVITY_TASK_COMPLETED)
    ]


def _child_id(change: Change) -> str:
    return child_workflow_id(
        change.kind.value, SLUG, change.head_sha, change.project_id, change.run
    )


async def _current_details(handle: WorkflowHandle) -> str:
    metadata = await handle.query("__temporal_workflow_metadata", result_type=WorkflowMetadata)
    return metadata.current_details


async def test_the_activity_result_in_the_history_carries_what_each_reviewer_answered(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await _persist(session_factory, sha="c" * 40)
    agents = {name: FakeAgent(name) for name in AGENTS}
    platform, agents_worker = _workers(temporal_env, session_factory, agents)

    async with platform, agents_worker:
        await _starter(temporal_env, session_factory).start(change)
        parent = temporal_env.client.get_workflow_handle(workflow_id(change, SLUG))
        await parent.result()
        child = temporal_env.client.get_workflow_handle(_child_id(change))
        history = await child.fetch_history()

    results = _completed_activity_results(history)
    assert sorted(r["agent"] for r in results) == AGENTS
    for result in results:
        assert result["status"] == "completed"
        assert result["summary"] == f"Revisión de {result['agent']} sobre ccccccc"
        assert result["score"] == 7
        assert result["findings"] == [
            {
                "severity": "nit",
                "file": "N/A",
                "line": 0,
                "message": "sin hallazgos reales (FakeAgent)",
            }
        ]
        assert result["findings_total"] == 1 and result["truncated"] is False
        assert "raw_output" not in result and "diff" not in result


async def test_the_result_of_the_child_and_the_parent_lists_the_answers_too(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await _persist(session_factory, sha="d" * 40)
    agents = {name: FakeAgent(name) for name in AGENTS}
    platform, agents_worker = _workers(temporal_env, session_factory, agents)

    async with platform, agents_worker:
        await _starter(temporal_env, session_factory).start(change)
        parent = temporal_env.client.get_workflow_handle(workflow_id(change, SLUG))
        await parent.result()
        history = await parent.fetch_history()

    (completed,) = _events(history, EventType.EVENT_TYPE_WORKFLOW_EXECUTION_COMPLETED)
    answers = CONVERTER.from_payload(
        completed.workflow_execution_completed_event_attributes.result.payloads[0]
    )
    assert sorted(a["agent"] for a in answers) == AGENTS
    assert all(a["summary"].startswith("Revisión de agent_") for a in answers)


async def test_every_activity_has_a_one_line_summary(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await _persist(session_factory, sha="5" * 40)
    agents = {name: FakeAgent(name) for name in AGENTS}
    platform, agents_worker = _workers(temporal_env, session_factory, agents)

    async with platform, agents_worker:
        await _starter(temporal_env, session_factory).start(change)
        await temporal_env.client.get_workflow_handle(workflow_id(change, SLUG)).result()
        history = await temporal_env.client.get_workflow_handle(_child_id(change)).fetch_history()

    scheduled = [
        CONVERTER.from_payload(event.user_metadata.summary)
        for event in _events(history, EventType.EVENT_TYPE_ACTIVITY_TASK_SCHEDULED)
    ]
    assert sorted(scheduled) == ["agent_1 revisa 5555555", "agent_2 revisa 5555555"]


async def test_the_workflows_carry_a_summary_and_a_card_in_the_list(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await _persist(session_factory, sha="7" * 40, title="feat: *algo*")
    agents = {name: FakeAgent(name) for name in AGENTS}
    platform, agents_worker = _workers(temporal_env, session_factory, agents)

    async with platform, agents_worker:
        await _starter(temporal_env, session_factory).start(change)
        parent = temporal_env.client.get_workflow_handle(workflow_id(change, SLUG))
        await parent.result()
        parent_description = await parent.describe()
        child_description = await temporal_env.client.get_workflow_handle(
            _child_id(change)
        ).describe()

    assert await parent_description.static_summary() == "commit · acme/widgets · feat: *algo*"
    assert await child_description.static_summary() == "review · acme/widgets · feat: *algo*"
    details = await child_description.static_details()
    assert details is not None
    assert "**Repositorio:** acme/widgets" in details
    assert "**Título:** feat: \\*algo\\*" in details  # el markdown del título no tiene efecto


async def test_the_child_publishes_one_line_per_agent_in_its_current_details(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await _persist(session_factory, sha="8" * 40)
    agents = {name: FakeAgent(name) for name in AGENTS}
    platform, agents_worker = _workers(temporal_env, session_factory, agents)

    async with platform, agents_worker:
        await _starter(temporal_env, session_factory).start(change)
        await temporal_env.client.get_workflow_handle(workflow_id(change, SLUG)).result()
        details = await _current_details(temporal_env.client.get_workflow_handle(_child_id(change)))

    lines = details.splitlines()
    assert lines[0] == "### Revisión de los agentes"
    done = "completada · 7/10 · 1 hallazgo (1 nit) — Revisión de"
    assert lines[2:] == [
        f"- ✅ **agent\\_1** · {done} agent\\_1 sobre 8888888",
        f"- ✅ **agent\\_2** · {done} agent\\_2 sobre 8888888",
    ]


async def test_a_failed_agent_shows_its_reason_next_to_the_one_that_worked(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await _persist(session_factory, sha="b" * 40)
    agents = {
        "agent_1": FakeAgent("agent_1"),
        "agent_2": FakeAgent("agent_2", should_fail=True, failure_message="sin sesión token=abc"),
    }
    platform, agents_worker = _workers(temporal_env, session_factory, agents)

    async with platform, agents_worker:
        await _starter(temporal_env, session_factory).start(change)
        await temporal_env.client.get_workflow_handle(workflow_id(change, SLUG)).result()
        child = temporal_env.client.get_workflow_handle(_child_id(change))
        details = await _current_details(child)
        history = await child.fetch_history()

    assert "✅ **agent\\_1** · completada" in details
    assert "❌ **agent\\_2** · fallida — sin sesión token=\\[oculto\\]" in details
    failed = next(r for r in _completed_activity_results(history) if r["status"] == "failed")
    assert failed["agent"] == "agent_2"
    assert failed["error"] == "sin sesión token=[oculto]"  # sin credenciales
    assert failed["summary"] is None and failed["findings"] == []


async def test_an_execution_started_without_presentation_data_keeps_the_old_child_id(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    """Un arranque con la entrada antigua (sin repo ni SHA) sigue funcionando: el hijo se llama
    como antes y no inventa un nombre."""
    change = await _persist(session_factory, sha="a" * 40)
    agents = {name: FakeAgent(name) for name in AGENTS}
    platform, agents_worker = _workers(temporal_env, session_factory, agents)

    async with platform, agents_worker:
        results = await temporal_env.client.execute_workflow(
            "ReviewCommitWorkflow",
            ReviewCommitInput(change_id=str(change.id), agent_names=AGENTS),
            id="parent-sin-datos",
            task_queue="platform",
        )
        legacy_child = temporal_env.client.get_workflow_handle(f"review-{change.id}-r1")
        description = await legacy_child.describe()

    assert len(results) == 2
    assert await description.static_summary() is None


@pytest.mark.parametrize("run", [1, 2])
async def test_an_execution_recorded_before_the_readable_names_still_replays(
    run: int, temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    """Versionado: la historia de una ejecución anterior (hijo `review-{change}-r{run}`, sin
    resúmenes ni detalles) se reproduce con el workflow nuevo sin errores de no determinismo."""
    change = await _persist(session_factory, sha=("1" if run == 1 else "2") * 40)
    agents = {name: FakeAgent(name) for name in AGENTS}
    activities = make_activities(session_factory, agents)
    async with (
        Worker(
            temporal_env.client,
            task_queue="platform",
            workflows=[
                ReviewCommitWorkflowBeforeReadableNames,
                ReviewChangeWorkflowBeforeCompensation,
            ],
        ),
        Worker(temporal_env.client, task_queue="agents", activities=[activities.run_review]),
    ):
        await temporal_env.client.execute_workflow(
            "ReviewCommitWorkflow",
            ReviewCommitInput(change_id=str(change.id), agent_names=AGENTS, run=run),
            id=f"commit-antiguo-{run}",
            task_queue="platform",
        )
        parent_history = await temporal_env.client.get_workflow_handle(
            f"commit-antiguo-{run}"
        ).fetch_history()
        child_history = await temporal_env.client.get_workflow_handle(
            f"review-{change.id}-r{run}"
        ).fetch_history()

    replayer = Replayer(workflows=[ReviewCommitWorkflow, ReviewChangeWorkflow])
    await replayer.replay_workflow(parent_history)
    await replayer.replay_workflow(child_history)


async def test_a_new_execution_replays_with_the_new_workflows(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    change = await _persist(session_factory, sha="3" * 40)
    agents = {name: FakeAgent(name) for name in AGENTS}
    platform, agents_worker = _workers(temporal_env, session_factory, agents)

    async with platform, agents_worker:
        await _starter(temporal_env, session_factory).start(change)
        parent = temporal_env.client.get_workflow_handle(workflow_id(change, SLUG))
        await parent.result()
        parent_history = await parent.fetch_history()
        child_history = await temporal_env.client.get_workflow_handle(
            _child_id(change)
        ).fetch_history()

    replayer = Replayer(workflows=[ReviewCommitWorkflow, ReviewChangeWorkflow])
    await replayer.replay_workflow(parent_history)
    await replayer.replay_workflow(child_history)


async def test_a_commit_and_a_pr_with_the_same_sha_are_both_reviewed(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    """Regresión: el hijo de la PR chocaba con el del commit (mismo repo y SHA) y su review no se
    hacía nunca."""
    sha = "4" * 40
    commit = await _persist(session_factory, sha=sha, kind=ChangeKind.COMMIT)
    pr = await _persist(session_factory, sha=sha, kind=ChangeKind.PR)
    agents = {name: FakeAgent(name) for name in AGENTS}
    platform, agents_worker = _workers(temporal_env, session_factory, agents)

    async with platform, agents_worker:
        starter = _starter(temporal_env, session_factory)
        await starter.start(commit)
        await starter.start(pr)
        for change in (commit, pr):
            await temporal_env.client.get_workflow_handle(workflow_id(change, SLUG)).result()

    assert _child_id(commit) != _child_id(pr)
    assert _child_id(commit).startswith("review-commit-") and _child_id(pr).startswith("review-pr-")
    assert len(await reviews_for(session_factory, commit)) == 2
    assert len(await reviews_for(session_factory, pr)) == 2


# Troceados: un literal con forma de credencial en el código lo marcaría el escáner de secretos.
LEAKED = ("abc123" + "tokenvalue", "sk-" + "abcdefghijklmnop1234", "hunter" + "2")


class LeakyAgent:
    """Un revisor que avisa de que hay credenciales en el diff y las cita."""

    name = "agent_1"

    async def review(self, change: Change) -> ReviewResult:
        return ReviewResult(
            summary="El diff trae token=abc123tokenvalue y la clave sk-abcdefghijklmnop1234.",
            score=2,
            findings=(
                Finding("bug", "src/config.py", 4, "password = hunter2 escrito en el código"),
            ),
        )


def _every_byte_of(history: WorkflowHistory) -> bytes:
    return b"".join(event.SerializeToString() for event in history.events)


async def test_no_credential_reaches_the_immutable_temporal_history(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    """Regresión: solo el error de una review fallida se saneaba; el resumen y los hallazgos de una
    review COMPLETADA, y el título del change (entrada del workflow y resúmenes estáticos), se
    copiaban tal cual al historial, que es inmutable. Se revisan los bytes de TODOS los eventos."""
    change = await _persist(session_factory, sha="9" * 40, title="fix: usar token=abc123tokenvalue")
    agents = {"agent_1": LeakyAgent(), "agent_2": FakeAgent("agent_2")}
    platform, agents_worker = _workers(temporal_env, session_factory, agents)

    async with platform, agents_worker:
        await _starter(temporal_env, session_factory).start(change)
        parent = temporal_env.client.get_workflow_handle(workflow_id(change, SLUG))
        await parent.result()
        child = temporal_env.client.get_workflow_handle(_child_id(change))
        parent_history, child_history = await parent.fetch_history(), await child.fetch_history()
        details = await _current_details(child)
        descriptions = [await parent.describe(), await child.describe()]
        statics = [
            text
            for description in descriptions
            for text in (await description.static_summary(), await description.static_details())
        ]

    stored = await reviews_for(session_factory, change)
    assert any("abc123tokenvalue" in (r.summary or "") for r in stored)  # el agente sí la citó
    everything = _every_byte_of(parent_history) + _every_byte_of(child_history)
    everything += (details + "".join(t or "" for t in statics)).encode()
    for secret in LEAKED:
        assert secret.encode() not in everything, secret
    # Lo demás de la respuesta sigue legible.
    results = {r["agent"]: r for r in _completed_activity_results(child_history)}
    assert results["agent_1"]["summary"] == "El diff trae token=[oculto] y la clave [oculto]."
    assert (
        results["agent_1"]["findings"][0]["message"] == "password = [oculto] escrito en el código"
    )
