from datetime import UTC, datetime
from uuid import uuid4

from review_arena.application.record_review import record_review_failure, record_review_success
from review_arena.domain.change import Change, ChangeKind
from review_arena.domain.review import Finding, ReviewResult
from tests.fakes.review_repository import FakeReviewRepository


def _make_change() -> Change:
    return Change.new(
        project_id=uuid4(),
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha="a" * 40,
        title="fix: algo",
        author="renzo",
        url="https://example.com",
        diff="diff --git a/x b/x",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )


async def test_record_review_success_persists_review_and_one_event() -> None:
    repo = FakeReviewRepository()
    change = _make_change()
    result = ReviewResult(summary="ok", score=9, findings=(Finding("nit", "a.py", 1, "x"),))

    review = await record_review_success(
        repo, change=change, agent="agent_1", run=1, result=result, raw_output="{}", duration_ms=500
    )

    assert review.status == "completed"
    assert len(repo.persisted_events) == 1
    assert repo.persisted_events[0].type == "review.completed"


async def test_record_review_failure_does_not_raise_and_persists_failed_review() -> None:
    repo = FakeReviewRepository()
    change = _make_change()

    review = await record_review_failure(
        repo, change=change, agent="agent_2", run=1, error="timeout", duration_ms=None
    )

    assert review.status == "failed"
    assert review.error == "timeout"
    assert len(repo.persisted_events) == 1
    assert repo.persisted_events[0].type == "review.failed"


async def test_reingesting_same_review_natural_key_is_idempotent() -> None:
    repo = FakeReviewRepository()
    change = _make_change()
    result = ReviewResult(summary="ok", score=9, findings=())

    first = await record_review_success(
        repo, change=change, agent="agent_1", run=1, result=result, raw_output=None, duration_ms=10
    )
    second = await record_review_success(
        repo, change=change, agent="agent_1", run=1, result=result, raw_output=None, duration_ms=10
    )

    assert first.id == second.id
    assert len(repo.persisted_events) == 1
