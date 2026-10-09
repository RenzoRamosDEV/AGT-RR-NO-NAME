"""Los casos de uso deben reenviar cada dato a la entidad y al evento (mata mutantes)."""

from datetime import UTC, datetime
from uuid import uuid4

from review_arena.application.ingest_change import ingest_change
from review_arena.application.record_review import record_review_failure, record_review_success
from review_arena.domain.change import Change, ChangeKind
from review_arena.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from review_arena.domain.review import Finding, ReviewResult
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.review_repository import FakeReviewRepository


async def test_ingest_change_forwards_every_field_to_the_change_and_the_event() -> None:
    repo = FakeChangeRepository()
    project_id = uuid4()
    before = datetime.now(UTC)

    change = await ingest_change(
        repo,
        project_id=project_id,
        kind=ChangeKind.PR,
        ref="refs/pull/9/head",
        head_sha="beef" * 10,
        title="titulo",
        author="autora",
        url="https://example.com/pull/9",
        diff="diff completo",
        diff_truncated=True,
    )

    after = datetime.now(UTC)
    assert (
        change.project_id,
        change.kind,
        change.ref,
        change.head_sha,
        change.title,
        change.author,
        change.url,
        change.diff,
        change.diff_truncated,
    ) == (
        project_id,
        ChangeKind.PR,
        "refs/pull/9/head",
        "beef" * 10,
        "titulo",
        "autora",
        "https://example.com/pull/9",
        "diff completo",
        True,
    )
    assert change.created_at.tzinfo is not None
    assert before <= change.created_at <= after

    (event,) = repo.persisted_events
    assert isinstance(event, ChangeCreated)
    assert (event.change_id, event.project_id, event.kind, event.head_sha) == (
        change.id,
        project_id,
        "pr",
        "beef" * 10,
    )


def _change() -> Change:
    return Change.new(
        project_id=uuid4(),
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha="a" * 40,
        title="t",
        author="a",
        url="https://example.com",
        diff="d",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )


async def test_record_review_success_forwards_every_field_to_review_and_event() -> None:
    repo = FakeReviewRepository()
    change = _change()
    result = ReviewResult("resumen", 9, (Finding("risk", "x.py", 4, "ojo"),))
    before = datetime.now(UTC)

    review = await record_review_success(
        repo,
        change=change,
        agent="agent_7",
        run=4,
        result=result,
        raw_output="crudo",
        duration_ms=321,
    )

    after = datetime.now(UTC)
    assert (review.change_id, review.agent, review.run) == (change.id, "agent_7", 4)
    assert (review.raw_output, review.duration_ms) == ("crudo", 321)
    assert (review.summary, review.score, review.findings) == (
        "resumen",
        9,
        (Finding("risk", "x.py", 4, "ojo"),),
    )
    assert review.created_at.tzinfo is not None
    assert before <= review.created_at <= after

    (event,) = repo.persisted_events
    assert isinstance(event, ReviewCompleted)
    assert (event.review_id, event.change_id, event.project_id, event.agent) == (
        review.id,
        change.id,
        change.project_id,
        "agent_7",
    )


async def test_record_review_failure_forwards_every_field_to_review_and_event() -> None:
    repo = FakeReviewRepository()
    change = _change()
    before = datetime.now(UTC)

    review = await record_review_failure(
        repo, change=change, agent="agent_8", run=5, error="se cayo", duration_ms=77
    )

    after = datetime.now(UTC)
    assert (review.change_id, review.agent, review.run) == (change.id, "agent_8", 5)
    assert (review.error, review.duration_ms) == ("se cayo", 77)
    assert review.created_at.tzinfo is not None
    assert before <= review.created_at <= after

    (event,) = repo.persisted_events
    assert isinstance(event, ReviewFailed)
    assert (event.review_id, event.change_id, event.project_id, event.agent, event.error) == (
        review.id,
        change.id,
        change.project_id,
        "agent_8",
        "se cayo",
    )


async def test_record_review_failure_duration_defaults_to_unknown() -> None:
    review = await record_review_failure(
        FakeReviewRepository(), change=_change(), agent="a", run=1, error="x"
    )

    assert review.duration_ms is None
