"""Nombres legibles de los workflows en Temporal y la guarda frente al id antiguo."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.client import WorkflowFailureError
from temporalio.service import RPCError, RPCStatusCode
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from duelo.adapters.agents.fake import FakeAgent
from duelo.adapters.orchestration.temporal_client import LazyTemporalClient
from duelo.adapters.orchestration.temporal_review_starter import TemporalReviewStarter, workflow_id
from duelo.application.ports import ReviewStartError
from duelo.application.review_requests import ReviewCommitInput
from duelo.application.task_queues import AGENTS_TASK_QUEUE, PLATFORM_TASK_QUEUE
from duelo.application.workflow_naming import legacy_parent_workflow_id
from duelo.domain.change import Change, ChangeKind
from duelo.workflows.review_change import ReviewChangeWorkflow
from duelo.workflows.review_commit import ReviewCommitWorkflow
from tests.fakes.project_slugs import FakeProjectSlugs
from tests.integration.helpers import make_activities, persist_change

SLUG = "acme/widgets"
AGENTS = ["agent_1", "agent_2"]


def _change(
    sha: str = "a" * 40,
    kind: ChangeKind = ChangeKind.COMMIT,
    project_id: UUID | None = None,
    title: str = "fix: algo",
) -> Change:
    return Change.new(
        project_id=project_id or uuid4(),
        kind=kind,
        ref="refs/heads/main",
        head_sha=sha,
        title=title,
        author="a",
        url="",
        diff="d",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )


def _starter(env: WorkflowEnvironment, slugs: FakeProjectSlugs | None = None):
    address = env.client.service_client.config.target_host
    return TemporalReviewStarter(
        LazyTemporalClient(address), AGENTS, slugs or FakeProjectSlugs(default=SLUG)
    )


async def _exists(env: WorkflowEnvironment, workflow: str) -> bool:
    try:
        await env.client.get_workflow_handle(workflow).describe()
    except RPCError as exc:
        if exc.status == RPCStatusCode.NOT_FOUND:
            return False
        raise
    return True


@asynccontextmanager
async def _workers(env: WorkflowEnvironment, session_factory: async_sessionmaker):
    activities = make_activities(session_factory, {name: FakeAgent(name) for name in AGENTS})
    async with (
        Worker(
            env.client,
            task_queue=PLATFORM_TASK_QUEUE,
            workflows=[ReviewChangeWorkflow, ReviewCommitWorkflow],
        ),
        Worker(
            env.client,
            task_queue=AGENTS_TASK_QUEUE,
            activities=[activities.run_review, activities.record_review_infrastructure_failure],
        ),
    ):
        yield


async def test_a_commit_is_named_after_its_kind_the_repo_and_the_sha(
    temporal_env: WorkflowEnvironment,
) -> None:
    change = _change(project_id=UUID("ab12cd34-0000-4000-8000-000000000001"))

    await _starter(temporal_env).start(change)

    expected = "commit-acme-widgets-aaaaaaaaaaaa-ab12cd"
    assert workflow_id(change, SLUG) == expected
    description = await temporal_env.client.get_workflow_handle(expected).describe()
    assert await description.static_summary() == "commit · acme/widgets · fix: algo"
    details = await description.static_details()
    assert details is not None
    assert "**Repositorio:** acme/widgets" in details and "**Tipo:** commit" in details


async def test_a_pr_is_named_with_its_own_prefix(temporal_env: WorkflowEnvironment) -> None:
    pr = _change(kind=ChangeKind.PR, project_id=UUID("ab12cd34-0000-4000-8000-000000000001"))

    await _starter(temporal_env).start(pr)

    assert await _exists(temporal_env, "pr-acme-widgets-aaaaaaaaaaaa-ab12cd")
    assert not await _exists(temporal_env, "commit-acme-widgets-aaaaaaaaaaaa-ab12cd")


async def test_a_readded_project_with_the_same_name_still_starts_its_review(
    temporal_env: WorkflowEnvironment,
) -> None:
    """Regresión: con un id solo con el nombre, volver a añadir un proyecto quitado y reenviar el
    mismo commit chocaba con la ejecución anterior y Temporal lo ignoraba en silencio."""
    before = _change(project_id=UUID("aaaaaaaa-0000-4000-8000-000000000001"))
    after = _change(project_id=UUID("bbbbbbbb-0000-4000-8000-000000000002"))
    starter = _starter(temporal_env)

    await starter.start(before)
    await starter.start(after)

    assert workflow_id(before, SLUG) != workflow_id(after, SLUG)
    assert await _exists(temporal_env, workflow_id(before, SLUG))
    assert await _exists(temporal_env, workflow_id(after, SLUG))


async def test_an_unknown_project_still_gets_a_valid_name(
    temporal_env: WorkflowEnvironment,
) -> None:
    change = _change(project_id=UUID("ab12cd34-0000-4000-8000-000000000001"))

    await _starter(temporal_env, FakeProjectSlugs()).start(change)

    assert await _exists(temporal_env, "commit-proyecto-aaaaaaaaaaaa-ab12cd")


async def test_a_failing_name_lookup_becomes_review_start_error(
    temporal_env: WorkflowEnvironment,
) -> None:
    class Broken:
        async def slug_of(self, project_id: UUID) -> str | None:
            raise OSError("base de datos caída")

    with pytest.raises(ReviewStartError):
        await _starter(temporal_env, Broken()).start(_change())  # type: ignore[arg-type]


# --- Guarda frente al id antiguo -------------------------------------------------------------


async def _start_legacy(env: WorkflowEnvironment, change: Change) -> str:
    """Arranca la review como lo hacía el starter anterior: id `{kind}-{proyecto}-{sha}` y una
    entrada sin datos de presentación."""
    legacy_id = legacy_parent_workflow_id(
        change.kind.value, change.project_id, change.head_sha, change.run
    )
    await env.client.start_workflow(
        "ReviewCommitWorkflow",
        ReviewCommitInput(change_id=str(change.id), agent_names=AGENTS, run=change.run),
        id=legacy_id,
        task_queue=PLATFORM_TASK_QUEUE,
    )
    return legacy_id


async def test_a_commit_still_running_under_the_old_id_is_not_started_again(
    temporal_env: WorkflowEnvironment,
) -> None:
    change = _change()
    await _start_legacy(temporal_env, change)

    await _starter(temporal_env).start(change)

    assert not await _exists(temporal_env, workflow_id(change, SLUG))


async def test_a_commit_already_reviewed_under_the_old_id_does_not_wake_the_agents_again(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    """Reenviar un commit revisado antes de los nombres legibles no debe gastar la suscripción
    del usuario lanzando a los agentes otra vez."""
    change = await persist_change(session_factory, "e" * 40)
    async with _workers(temporal_env, session_factory):
        legacy_id = await _start_legacy(temporal_env, change)
        await temporal_env.client.get_workflow_handle(legacy_id).result()

        await _starter(temporal_env).start(change)

    assert not await _exists(temporal_env, workflow_id(change, SLUG))


async def test_a_commit_that_failed_under_the_old_id_can_be_started_under_the_new_one(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    ghost = _change("f" * 40)  # no está en la base de datos: la ejecución antigua termina en fallo
    async with _workers(temporal_env, session_factory):
        legacy_id = await _start_legacy(temporal_env, ghost)
        with pytest.raises(WorkflowFailureError):
            await temporal_env.client.get_workflow_handle(legacy_id).result()

        await _starter(temporal_env).start(ghost)

    assert await _exists(temporal_env, workflow_id(ghost, SLUG))


async def test_the_second_run_is_guarded_by_its_own_old_id(
    temporal_env: WorkflowEnvironment,
) -> None:
    first = _change()
    second = replace(first, run=2)
    await _start_legacy(temporal_env, second)  # solo el run 2 arrancó con el id antiguo

    starter = _starter(temporal_env)
    await starter.start(second)
    await starter.start(first)

    assert not await _exists(temporal_env, workflow_id(second, SLUG))
    assert await _exists(temporal_env, workflow_id(first, SLUG))
