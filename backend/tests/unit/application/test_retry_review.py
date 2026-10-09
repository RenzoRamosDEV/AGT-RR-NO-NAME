import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from duelo.application.ports import ReviewStartError
from duelo.application.retry_review import ChangeNotFound, RetryNotAllowed, retry_review
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.review import Review, ReviewResult
from duelo.domain.review_status import ChangeReviewStatus
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.review_repository import FakeReviewRepository
from tests.fakes.review_starter import FakeReviewStarter

NOW = datetime(2026, 1, 1, tzinfo=UTC)
AGENTS = ("a", "b")


async def _change(repo: FakeChangeRepository) -> Change:
    change = Change.new(
        project_id=uuid4(),
        kind=ChangeKind.PR,
        ref="refs/pull/1/head",
        head_sha="c" * 40,
        title="t",
        author="a",
        url="u",
        diff="d",
        diff_truncated=False,
        created_at=NOW,
    )
    event = ChangeCreated(
        change_id=change.id, project_id=change.project_id, kind="pr", head_sha=change.head_sha
    )
    return await repo.add(change, event)


async def _review(
    reviews: FakeReviewRepository, change: Change, agent: str, *, fail: bool, run: int = 1
) -> None:
    ids = {"change_id": change.id, "agent": agent, "run": run, "created_at": NOW}
    if fail:
        review = Review.failed(error="boom", duration_ms=None, **ids)
        event = ReviewFailed(
            review_id=review.id,
            change_id=change.id,
            project_id=change.project_id,
            agent=agent,
            error="boom",
        )
    else:
        review = Review.succeeded(
            result=ReviewResult(summary="ok", score=5), raw_output=None, duration_ms=1, **ids
        )
        event = ReviewCompleted(
            review_id=review.id, change_id=change.id, project_id=change.project_id, agent=agent
        )
    await reviews.add(review, event)


def _world() -> tuple[FakeChangeRepository, FakeReviewRepository]:
    reviews = FakeReviewRepository()
    return FakeChangeRepository(reviews), reviews


async def _retry(
    changes: FakeChangeRepository,
    reviews: FakeReviewRepository,
    starter: FakeReviewStarter,
    change: Change,
) -> Change:
    return await retry_review(changes, reviews, starter, change.id, expected_agents=len(AGENTS))


@pytest.mark.parametrize("fails", [(True, True), (True, False)], ids=["failed", "partial_failed"])
async def test_a_failed_execution_starts_the_next_run_and_advances_run(
    fails: tuple[bool, bool],
) -> None:
    changes, reviews = _world()
    starter = FakeReviewStarter()
    change = await _change(changes)
    for agent, fail in zip(AGENTS, fails, strict=True):
        await _review(reviews, change, agent, fail=fail)

    retried = await _retry(changes, reviews, starter, change)

    assert retried.run == 2
    assert (await changes.get(change.id)) == retried
    # El arranque lleva el run nuevo: el workflow id del run 1 no se reutiliza.
    started = starter.started[("pr", str(change.project_id), change.head_sha, 2)]
    assert started.id == change.id and started.run == 2
    assert starter.calls == 1


@pytest.mark.parametrize(
    "reviews_for",
    [
        pytest.param([], id="pending"),
        pytest.param([("a", True)], id="running"),
        pytest.param([("a", False), ("b", False)], id="completed"),
    ],
)
async def test_other_states_are_not_retryable_and_start_nothing(
    reviews_for: list[tuple[str, bool]],
) -> None:
    changes, reviews = _world()
    starter = FakeReviewStarter()
    change = await _change(changes)
    for agent, fail in reviews_for:
        await _review(reviews, change, agent, fail=fail)

    with pytest.raises(RetryNotAllowed):
        await _retry(changes, reviews, starter, change)

    assert starter.calls == 0
    assert (await changes.get(change.id)) == change  # run intacto


async def test_the_reason_names_the_status_that_blocked_the_retry() -> None:
    changes, reviews = _world()
    change = await _change(changes)
    await _review(reviews, change, "a", fail=False)
    await _review(reviews, change, "b", fail=False)

    with pytest.raises(RetryNotAllowed) as error:
        await _retry(changes, reviews, FakeReviewStarter(), change)

    assert error.value.status is ChangeReviewStatus.COMPLETED
    assert "completed" in str(error.value)


async def test_unknown_change() -> None:
    changes, reviews = _world()
    missing = uuid4()

    with pytest.raises(ChangeNotFound) as error:
        await retry_review(changes, reviews, FakeReviewStarter(), missing, expected_agents=2)

    assert error.value.change_id == missing


async def test_a_starter_failure_does_not_advance_run_so_the_retry_can_be_repeated() -> None:
    changes, reviews = _world()
    change = await _change(changes)
    await _review(reviews, change, "a", fail=True)
    await _review(reviews, change, "b", fail=True)

    with pytest.raises(ReviewStartError):
        await _retry(changes, reviews, FakeReviewStarter(fail=True), change)
    assert (await changes.get(change.id)).run == 1  # type: ignore[union-attr]

    healthy = FakeReviewStarter()
    assert (await _retry(changes, reviews, healthy, change)).run == 2


async def test_a_retried_change_must_fail_again_before_it_can_be_retried_again() -> None:
    changes, reviews = _world()
    starter = FakeReviewStarter()
    change = await _change(changes)
    await _review(reviews, change, "a", fail=True)
    await _review(reviews, change, "b", fail=True)
    await _retry(changes, reviews, starter, change)

    # Run 2 sin reviews todavía: pendiente, no reintentable (las del run 1 ya no cuentan).
    with pytest.raises(RetryNotAllowed):
        await _retry(changes, reviews, starter, change)

    await _review(reviews, change, "a", fail=True, run=2)
    await _review(reviews, change, "b", fail=True, run=2)
    assert (await _retry(changes, reviews, starter, change)).run == 3
    assert ("pr", str(change.project_id), change.head_sha, 3) in starter.started


async def test_two_simultaneous_retries_start_one_execution_and_advance_run_once() -> None:
    changes, reviews = _world()
    # El starter cede el control: ambas peticiones pasan la comprobación de estado antes de avanzar.
    starter = FakeReviewStarter(yield_on_start=True)
    change = await _change(changes)
    await _review(reviews, change, "a", fail=True)
    await _review(reviews, change, "b", fail=True)

    first, second = await asyncio.gather(
        _retry(changes, reviews, starter, change), _retry(changes, reviews, starter, change)
    )

    assert first.run == second.run == 2
    assert (await changes.get(change.id)).run == 2  # type: ignore[union-attr]
    assert len(starter.started) == 1  # mismo id de workflow: una sola ejecución del run 2


async def test_a_change_deleted_between_the_check_and_the_swap_is_reported_as_not_found() -> None:
    class VanishingChanges(FakeChangeRepository):
        async def advance_run(self, change_id: UUID, *, from_run: int) -> Change | None:
            self._by_id.pop(change_id)
            return None

    reviews = FakeReviewRepository()
    changes = VanishingChanges(reviews)
    change = await _change(changes)
    await _review(reviews, change, "a", fail=True)
    await _review(reviews, change, "b", fail=True)

    with pytest.raises(ChangeNotFound, match=str(change.id)):
        await _retry(changes, reviews, FakeReviewStarter(), change)


async def test_not_found_carries_the_id_in_its_message() -> None:
    missing = uuid4()

    with pytest.raises(ChangeNotFound, match=str(missing)):
        await retry_review(*_world(), FakeReviewStarter(), missing, expected_agents=2)
