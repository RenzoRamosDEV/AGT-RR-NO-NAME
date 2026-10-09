from datetime import UTC, datetime
from uuid import uuid4

import pytest
from temporalio.testing import WorkflowEnvironment

from review_arena.adapters.orchestration.temporal_client import LazyTemporalClient
from review_arena.adapters.orchestration.temporal_review_starter import TemporalReviewStarter
from review_arena.application.ports import ReviewStartError
from review_arena.domain.change import Change, ChangeKind


def _change(head_sha: str = "a" * 40) -> Change:
    return Change.new(
        project_id=uuid4(),
        kind=ChangeKind.COMMIT,
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


async def test_an_unreachable_temporal_becomes_review_start_error() -> None:
    starter = TemporalReviewStarter(LazyTemporalClient("127.0.0.1:1"), ["agent_1"])

    with pytest.raises(ReviewStartError):
        await starter.start(_change())
