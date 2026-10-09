from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.client import WorkflowFailureError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from duelo.adapters.agents.fake import FakeAgent
from duelo.adapters.orchestration.temporal_client import LazyTemporalClient
from duelo.adapters.orchestration.temporal_review_starter import TemporalReviewStarter
from duelo.application.ports import ReviewStartError
from duelo.domain.change import Change, ChangeKind
from duelo.workflows.review_change import ReviewChangeWorkflow
from duelo.workflows.review_commit import ReviewCommitWorkflow
from tests.integration.helpers import make_activities, persist_change


def _change(
    head_sha: str = "a" * 40, kind: ChangeKind = ChangeKind.COMMIT, project_id: UUID | None = None
) -> Change:
    return Change.new(
        project_id=project_id or uuid4(),
        kind=kind,
        ref="refs/heads/main",
        head_sha=head_sha,
        title="t",
        author="a",
        url="",
        diff="d",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )


def _starter(env: WorkflowEnvironment) -> TemporalReviewStarter:
    address = env.client.service_client.config.target_host
    return TemporalReviewStarter(LazyTemporalClient(address), ["agent_1", "agent_2"])


async def test_starting_the_same_commit_twice_keeps_a_single_execution(
    temporal_env: WorkflowEnvironment,
) -> None:
    starter = _starter(temporal_env)
    change = _change()
    workflow_id = f"commit-{change.project_id}-{change.head_sha}"

    await starter.start(change)
    first = await temporal_env.client.get_workflow_handle(workflow_id).describe()
    await starter.start(change)  # no lanza: WorkflowAlreadyStarted cuenta como éxito
    second = await temporal_env.client.get_workflow_handle(workflow_id).describe()

    assert first.run_id == second.run_id


async def test_different_commits_start_different_workflows(
    temporal_env: WorkflowEnvironment,
) -> None:
    starter = _starter(temporal_env)
    one, two = _change("a" * 40), _change("b" * 40)

    await starter.start(one)
    await starter.start(two)

    ids = {
        (
            await temporal_env.client.get_workflow_handle(
                f"commit-{c.project_id}-{c.head_sha}"
            ).describe()
        ).run_id
        for c in (one, two)
    }
    assert len(ids) == 2


async def test_a_pr_and_a_commit_with_the_same_sha_do_not_clash(
    temporal_env: WorkflowEnvironment,
) -> None:
    starter = _starter(temporal_env)
    project_id = uuid4()
    commit = _change(project_id=project_id)
    pr = _change(kind=ChangeKind.PR, project_id=project_id)

    await starter.start(commit)
    await starter.start(pr)

    # El id del commit conserva su forma histórica; el del PR lleva su propio prefijo.
    runs = {
        kind: (
            await temporal_env.client.get_workflow_handle(
                f"{kind}-{project_id}-{commit.head_sha}"
            ).describe()
        ).run_id
        for kind in ("commit", "pr")
    }
    assert runs["commit"] != runs["pr"]


async def test_an_unreachable_temporal_becomes_review_start_error() -> None:
    starter = TemporalReviewStarter(LazyTemporalClient("127.0.0.1:1"), ["agent_1"])

    with pytest.raises(ReviewStartError):
        await starter.start(_change())


@asynccontextmanager
async def _workers(env: WorkflowEnvironment, session_factory: async_sessionmaker):
    agents = {name: FakeAgent(name) for name in ("agent_1", "agent_2")}
    activities = make_activities(session_factory, agents)
    async with (
        Worker(
            env.client,
            task_queue="platform",
            workflows=[ReviewChangeWorkflow, ReviewCommitWorkflow],
        ),
        Worker(env.client, task_queue="agents", activities=[activities.run_review]),
    ):
        yield


async def test_a_completed_review_is_not_started_again(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    starter = _starter(temporal_env)
    change = await persist_change(session_factory, "c" * 40)
    workflow_id = f"commit-{change.project_id}-{change.head_sha}"

    async with _workers(temporal_env, session_factory):
        await starter.start(change)
        handle = temporal_env.client.get_workflow_handle(workflow_id)
        await handle.result()
        first = (await handle.describe()).run_id

        await starter.start(change)  # reenvío con la review ya completada

    assert (await handle.describe()).run_id == first


async def test_a_failed_review_can_be_started_again(
    temporal_env: WorkflowEnvironment, session_factory: async_sessionmaker
) -> None:
    starter = _starter(temporal_env)
    ghost = _change("d" * 40)  # no existe en la base de datos: el workflow termina en fallo
    workflow_id = f"commit-{ghost.project_id}-{ghost.head_sha}"

    async with _workers(temporal_env, session_factory):
        await starter.start(ghost)
        handle = temporal_env.client.get_workflow_handle(workflow_id)
        with pytest.raises(WorkflowFailureError):
            await handle.result()
        first = (await handle.describe()).run_id

        await starter.start(ghost)

    assert (await temporal_env.client.get_workflow_handle(workflow_id).describe()).run_id != first
