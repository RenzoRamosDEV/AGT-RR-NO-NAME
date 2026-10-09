from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.domain.events import ReviewCompleted
from duelo.domain.review import Review, ReviewResult


def _make_review(change_id, agent: str = "agent_1") -> Review:
    return Review.succeeded(
        change_id=change_id,
        agent=agent,
        run=1,
        result=ReviewResult(summary="ok", score=8, findings=()),
        raw_output=None,
        duration_ms=100,
        created_at=datetime.now(UTC),
    )


async def test_add_inserts_event_when_insert_succeeds() -> None:
    change_id = uuid4()
    review = _make_review(change_id)
    event = ReviewCompleted(
        review_id=review.id, change_id=change_id, project_id=uuid4(), agent=review.agent
    )

    insert_result = MagicMock()
    insert_result.scalar_one_or_none.return_value = review.id
    event_insert_result = MagicMock()

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[insert_result, event_insert_result])
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)

    repo = SqlAlchemyReviewRepository(session)
    result = await repo.add(review, event)

    assert result is review
    assert session.execute.await_count == 2


async def test_add_returns_existing_review_when_insert_conflicts() -> None:
    change_id = uuid4()
    review = _make_review(change_id)
    event = ReviewCompleted(
        review_id=review.id, change_id=change_id, project_id=uuid4(), agent=review.agent
    )

    existing_row = MagicMock()
    existing_row.id = uuid4()
    existing_row.change_id = change_id
    existing_row.agent = review.agent
    existing_row.run = review.run
    existing_row.status = review.status
    existing_row.summary = review.summary
    existing_row.score = review.score
    existing_row.findings = []
    existing_row.raw_output = review.raw_output
    existing_row.duration_ms = review.duration_ms
    existing_row.error = review.error
    existing_row.created_at = review.created_at

    insert_result = MagicMock()
    insert_result.scalar_one_or_none.return_value = None
    select_result = MagicMock()
    select_result.scalar_one.return_value = existing_row

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[insert_result, select_result])
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)

    repo = SqlAlchemyReviewRepository(session)
    result = await repo.add(review, event)

    assert result.id == existing_row.id
    assert session.execute.await_count == 2
