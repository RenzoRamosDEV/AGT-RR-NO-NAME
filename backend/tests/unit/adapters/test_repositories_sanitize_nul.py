"""Lo que llega a la sentencia INSERT no contiene NUL (sesión mockeada, sin Postgres)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from review_arena.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from review_arena.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from review_arena.domain.change import Change, ChangeKind
from review_arena.domain.events import ChangeCreated, ReviewCompleted
from review_arena.domain.review import Finding, Review, ReviewResult

NUL = "\x00"


def _session(first_result_scalar: object) -> MagicMock:
    first = MagicMock()
    first.scalar_one_or_none.return_value = first_result_scalar
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[first, MagicMock()])
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    return session


def _params(session: MagicMock, call_index: int) -> dict[str, object]:
    statement = session.execute.await_args_list[call_index].args[0]
    return dict(statement.compile(dialect=postgresql.dialect()).params)


def _flatten(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for v in value for s in _flatten(v)]
    if isinstance(value, dict):
        return [s for k, v in value.items() for s in _flatten(k) + _flatten(v)]
    return []


async def test_change_repository_sanitizes_title_author_and_diff() -> None:
    change = Change.new(
        project_id=uuid4(),
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha="a" * 40,
        title=f"ti{NUL}tle",
        author=f"au{NUL}thor",
        url="https://example.com",
        diff=f"d{NUL}iff",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )
    event = ChangeCreated(change.id, change.project_id, "commit", change.head_sha)
    session = _session(first_result_scalar=change.id)

    await SqlAlchemyChangeRepository(session).add(change, event)

    params = _params(session, 0)
    assert params["title"] == "ti�tle"
    assert params["author"] == "au�thor"
    assert params["diff"] == "d�iff"
    assert all(NUL not in s for s in _flatten(list(params.values())))


async def test_review_repository_sanitizes_summary_output_error_and_findings() -> None:
    review = Review.succeeded(
        change_id=uuid4(),
        agent="agent_1",
        run=1,
        result=ReviewResult(
            summary=f"su{NUL}mmary",
            score=5,
            findings=(Finding(f"se{NUL}v", f"fi{NUL}le", 3, f"me{NUL}ssage"),),
        ),
        raw_output=f"ra{NUL}w",
        duration_ms=1,
        created_at=datetime.now(UTC),
    )
    event = ReviewCompleted(review.id, review.change_id, uuid4(), "agent_1")
    session = _session(first_result_scalar=review.id)

    await SqlAlchemyReviewRepository(session).add(review, event)

    params = _params(session, 0)
    assert params["summary"] == "su�mmary"
    assert params["raw_output"] == "ra�w"
    assert all(NUL not in s for s in _flatten(list(params.values())))


async def test_review_repository_sanitizes_the_error_of_a_failed_review() -> None:
    review = Review.failed(
        change_id=uuid4(),
        agent="agent_2",
        run=1,
        error=f"bo{NUL}om",
        duration_ms=None,
        created_at=datetime.now(UTC),
    )
    from review_arena.domain.events import ReviewFailed

    event = ReviewFailed(review.id, review.change_id, uuid4(), "agent_2", "boom")
    session = _session(first_result_scalar=review.id)

    await SqlAlchemyReviewRepository(session).add(review, event)

    assert _params(session, 0)["error"] == "bo�om"
