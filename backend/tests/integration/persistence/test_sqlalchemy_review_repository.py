"""Test de integración con testcontainers (Postgres real). Fixtures en conftest.py."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from review_arena.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from review_arena.adapters.persistence.models import EventModel, ReviewModel
from review_arena.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from review_arena.application.ingest_change import ingest_change
from review_arena.application.record_review import record_review_failure, record_review_success
from review_arena.domain.change import Change, ChangeKind
from review_arena.domain.review import ReviewResult
from tests.integration.conftest import create_project


async def _create_change(session_factory: async_sessionmaker, head_sha: str) -> Change:
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


async def test_two_agents_persist_two_reviews_for_the_same_change(
    session_factory: async_sessionmaker,
) -> None:
    change = await _create_change(session_factory, head_sha="a" * 40)
    result = ReviewResult(summary="todo bien", score=8, findings=())

    async with session_factory() as session:
        await record_review_success(
            SqlAlchemyReviewRepository(session),
            change=change,
            agent="agent_1",
            run=1,
            result=result,
            raw_output=None,
            duration_ms=100,
        )
    async with session_factory() as session:
        await record_review_success(
            SqlAlchemyReviewRepository(session),
            change=change,
            agent="agent_2",
            run=1,
            result=result,
            raw_output=None,
            duration_ms=120,
        )

    async with session_factory() as session:
        reviews = (
            (await session.execute(select(ReviewModel).where(ReviewModel.change_id == change.id)))
            .scalars()
            .all()
        )

    assert {r.agent for r in reviews} == {"agent_1", "agent_2"}


async def test_reregistering_same_review_natural_key_is_idempotent(
    session_factory: async_sessionmaker,
) -> None:
    change = await _create_change(session_factory, head_sha="b" * 40)
    result = ReviewResult(summary="ok", score=9, findings=())

    async def _record() -> None:
        async with session_factory() as session:
            await record_review_success(
                SqlAlchemyReviewRepository(session),
                change=change,
                agent="agent_1",
                run=1,
                result=result,
                raw_output=None,
                duration_ms=100,
            )

    await _record()
    await _record()

    async with session_factory() as session:
        reviews = (
            (await session.execute(select(ReviewModel).where(ReviewModel.change_id == change.id)))
            .scalars()
            .all()
        )
        events = (
            (await session.execute(select(EventModel).where(EventModel.type == "review.completed")))
            .scalars()
            .all()
        )

    assert len(reviews) == 1
    assert len([e for e in events if str(change.id) in str(e.payload.get("change_id"))]) == 1


async def test_failed_review_persists_with_failed_event(
    session_factory: async_sessionmaker,
) -> None:
    change = await _create_change(session_factory, head_sha="c" * 40)

    async with session_factory() as session:
        review = await record_review_failure(
            SqlAlchemyReviewRepository(session),
            change=change,
            agent="agent_2",
            run=1,
            error="timeout simulado",
        )

    assert review.status == "failed"

    async with session_factory() as session:
        events = (
            (await session.execute(select(EventModel).where(EventModel.type == "review.failed")))
            .scalars()
            .all()
        )

    matching = [e for e in events if e.payload.get("change_id") == str(change.id)]
    assert len(matching) == 1
    assert matching[0].payload.get("error") == "timeout simulado"
