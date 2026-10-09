from datetime import UTC, datetime
from uuid import uuid4

import pytest

from review_arena.domain.review import Finding, Review, ReviewResult, ReviewStatus


def test_succeeded_review_keeps_result_fields() -> None:
    result = ReviewResult(
        summary="todo bien",
        score=8,
        findings=(Finding(severity="nit", file="a.py", line=1, message="estilo"),),
    )

    review = Review.succeeded(
        change_id=uuid4(),
        agent="agent_1",
        run=1,
        result=result,
        raw_output='{"summary": "todo bien"}',
        duration_ms=1200,
        created_at=datetime.now(UTC),
    )

    assert review.status is ReviewStatus.COMPLETED
    assert review.status == "completed"
    assert review.summary == "todo bien"
    assert review.score == 8
    assert len(review.findings) == 1
    assert review.error is None


def test_failed_review_has_no_result_fields() -> None:
    review = Review.failed(
        change_id=uuid4(),
        agent="agent_2",
        run=1,
        error="timeout",
        duration_ms=None,
        created_at=datetime.now(UTC),
    )

    assert review.status is ReviewStatus.FAILED
    assert review.status == "failed"
    assert review.summary is None
    assert review.score is None
    assert review.findings == ()
    assert review.error == "timeout"


def test_failed_review_requires_an_error_message() -> None:
    with pytest.raises(ValueError):
        Review.failed(
            change_id=uuid4(),
            agent="agent_2",
            run=1,
            error="",
            duration_ms=None,
            created_at=datetime.now(UTC),
        )
