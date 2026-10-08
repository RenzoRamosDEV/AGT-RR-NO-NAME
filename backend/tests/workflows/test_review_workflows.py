"""Tests de los workflows de Temporal con WorkflowEnvironment.start_time_skipping()
(servidor de test efímero, sin necesidad de Temporal real ni Docker Compose).

Requiere testcontainers para el Postgres real donde vive el Change ya persistido -
mismas fixtures de tests/adapters/conftest.py (database_url, session_factory).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from review_arena.adapters.agents.fake import FakeAgent
from review_arena.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from review_arena.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from review_arena.application.ingest_change import ingest_change
from review_arena.domain.change import Change, ChangeKind
from review_arena.workflows.activities import ReviewActivities
from review_arena.workflows.review_change import ReviewChangeWorkflow
from review_arena.workflows.review_commit import ReviewCommitWorkflow
from tests.conftest import create_project


async def _persist_change(session_factory: async_sessionmaker, head_sha: str) -> Change:
    project_id = await create_project(session_factory)
    async with session_factory() as session:
        return await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=project_id,
            kind=ChangeKind.COMMIT,
            ref="refs/heads/main",
            head_sha=head_sha,
            title="fix: algo",
            author="renzo",
            url="https://example.com/commit/" + head_sha,
            diff="diff --git a/x b/x",
            diff_truncated=False,
        )


@pytest.fixture
async def temporal_env() -> AsyncIterator[WorkflowEnvironment]:
    async with await WorkflowEnvironment.start_time_skipping() as env:
        yield env


async def _run_with_workers[T](
    env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
    agents: dict[str, FakeAgent],
    body: Callable[[WorkflowEnvironment], Awaitable[T]],
) -> T:
    activities = ReviewActivities(
        session_factory=session_factory,
        change_repository=SqlAlchemyChangeRepository,
        review_repository=SqlAlchemyReviewRepository,
        agents=agents,  # type: ignore[arg-type]
    )
    async with (
        Worker(
            env.client,
            task_queue="platform",
            workflows=[ReviewChangeWorkflow, ReviewCommitWorkflow],
            activities=[activities.load_change],
        ),
        Worker(
            env.client,
            task_queue="agents",
            activities=[activities.run_review],
        ),
    ):
        return await body(env)


async def test_two_agents_produce_two_reviews(
    temporal_env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
) -> None:
    change = await _persist_change(session_factory, head_sha="a" * 40)
    agents = {"agent_1": FakeAgent("agent_1"), "agent_2": FakeAgent("agent_2")}

    async def _run(env: WorkflowEnvironment):
        return await env.client.execute_workflow(
            ReviewChangeWorkflow.run,
            args=[str(change.id), ["agent_1", "agent_2"]],
            id=f"review-{change.id}",
            task_queue="platform",
        )

    results = await _run_with_workers(temporal_env, session_factory, agents, _run)

    assert len(results) == 2
    assert {r.status for r in results} == {"completed"}
    assert len({r.review_id for r in results}) == 2


async def test_partial_failure_does_not_lose_the_successful_review(
    temporal_env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
) -> None:
    change = await _persist_change(session_factory, head_sha="b" * 40)
    agents = {
        "agent_1": FakeAgent("agent_1"),
        "agent_2": FakeAgent("agent_2", should_fail=True, failure_message="boom"),
    }

    async def _run(env: WorkflowEnvironment):
        return await env.client.execute_workflow(
            ReviewChangeWorkflow.run,
            args=[str(change.id), ["agent_1", "agent_2"]],
            id=f"review-{change.id}",
            task_queue="platform",
        )

    results = await _run_with_workers(temporal_env, session_factory, agents, _run)

    assert {r.status for r in results} == {"completed", "failed"}


async def test_review_commit_workflow_starts_the_child_and_returns_its_result(
    temporal_env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
) -> None:
    change = await _persist_change(session_factory, head_sha="c" * 40)
    agents = {"agent_1": FakeAgent("agent_1"), "agent_2": FakeAgent("agent_2")}

    async def _run(env: WorkflowEnvironment):
        return await env.client.execute_workflow(
            ReviewCommitWorkflow.run,
            args=[str(change.id), ["agent_1", "agent_2"]],
            id=f"commit-{change.id}",
            task_queue="platform",
        )

    results = await _run_with_workers(temporal_env, session_factory, agents, _run)

    assert len(results) == 2
    assert {r.status for r in results} == {"completed"}


async def test_starting_same_workflow_id_twice_while_running_is_rejected(
    temporal_env: WorkflowEnvironment,
    session_factory: async_sessionmaker,
) -> None:
    """Prueba la deduplicación nativa de Temporal por workflow_id: arrancar el mismo
    commit dos veces no produce dos ejecuciones concurrentes - la segunda falla."""
    change = await _persist_change(session_factory, head_sha="d" * 40)
    agents = {"agent_1": FakeAgent("agent_1"), "agent_2": FakeAgent("agent_2")}

    async def _run(env: WorkflowEnvironment) -> bool:
        workflow_id = f"commit-{change.id}"
        await env.client.start_workflow(
            ReviewCommitWorkflow.run,
            args=[str(change.id), ["agent_1", "agent_2"]],
            id=workflow_id,
            task_queue="platform",
        )

        try:
            await env.client.start_workflow(
                ReviewCommitWorkflow.run,
                args=[str(change.id), ["agent_1", "agent_2"]],
                id=workflow_id,
                task_queue="platform",
            )
        except WorkflowAlreadyStartedError:
            return True
        return False

    was_rejected = await _run_with_workers(temporal_env, session_factory, agents, _run)

    assert was_rejected is True
