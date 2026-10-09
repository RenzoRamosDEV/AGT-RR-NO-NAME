from __future__ import annotations

from datetime import UTC, datetime

from duelo.application.ports import ReviewRepository
from duelo.domain.change import Change
from duelo.domain.events import ReviewCompleted, ReviewFailed
from duelo.domain.review import Review, ReviewResult


async def record_review_success(
    repository: ReviewRepository,
    *,
    change: Change,
    agent: str,
    run: int,
    result: ReviewResult,
    raw_output: str | None,
    duration_ms: int,
) -> Review:
    review = Review.succeeded(
        change_id=change.id,
        agent=agent,
        run=run,
        result=result,
        raw_output=raw_output,
        duration_ms=duration_ms,
        created_at=datetime.now(UTC),
    )
    event = ReviewCompleted(
        review_id=review.id,
        change_id=change.id,
        project_id=change.project_id,
        agent=agent,
    )
    return await repository.add(review, event)


async def record_review_failure(
    repository: ReviewRepository,
    *,
    change: Change,
    agent: str,
    run: int,
    error: str,
    duration_ms: int | None = None,
) -> Review:
    review = Review.failed(
        change_id=change.id,
        agent=agent,
        run=run,
        error=error,
        duration_ms=duration_ms,
        created_at=datetime.now(UTC),
    )
    event = ReviewFailed(
        review_id=review.id,
        change_id=change.id,
        project_id=change.project_id,
        agent=agent,
        error=error,
    )
    return await repository.add(review, event)
