"""Invariantes de estado: lo único "máquina de estados" real que existe hoy.

`Change` solo tiene el estado `pending` y `Review` es terminal desde que se crea. Se prueba
lo real: combinaciones coherentes, entidades inmutables y enums cerrados. La máquina de
estados de `Change` (pending -> reviewing -> done/failed) llega con `finish_change`.
"""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from review_arena.domain.change import Change, ChangeKind, ChangeStatus
from review_arena.domain.review import Finding, Review, ReviewResult, ReviewStatus


def _succeeded() -> Review:
    return Review.succeeded(
        change_id=uuid4(),
        agent="a",
        run=1,
        result=ReviewResult("r", 5, (Finding("nit", "f.py", 1, "m"),)),
        raw_output="raw",
        duration_ms=3,
        created_at=datetime.now(UTC),
    )


def _failed() -> Review:
    return Review.failed(
        change_id=uuid4(),
        agent="a",
        run=1,
        error="x",
        duration_ms=None,
        created_at=datetime.now(UTC),
    )


def _change() -> Change:
    return Change.new(
        project_id=uuid4(),
        kind=ChangeKind.COMMIT,
        ref="r",
        head_sha="a" * 40,
        title="t",
        author="a",
        url="u",
        diff="d",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )


def test_a_completed_review_never_carries_an_error() -> None:
    review = _succeeded()

    assert review.status is ReviewStatus.COMPLETED
    assert review.error is None


def test_a_failed_review_never_carries_result_data() -> None:
    review = _failed()

    assert review.status is ReviewStatus.FAILED
    assert (review.summary, review.score, review.findings, review.raw_output) == (
        None,
        None,
        (),
        None,
    )


def test_a_new_change_always_starts_pending_at_run_one() -> None:
    change = _change()

    assert (change.status, change.run) == (ChangeStatus.PENDING, 1)


@pytest.mark.parametrize("entity", [_succeeded, _failed, _change], ids=["ok", "failed", "change"])
def test_entities_are_immutable(entity) -> None:
    instance = entity()

    with pytest.raises(FrozenInstanceError):
        instance.status = "otra-cosa"  # type: ignore[misc]


@pytest.mark.parametrize("enum", [ReviewStatus, ChangeStatus, ChangeKind])
def test_enums_are_closed(enum) -> None:
    with pytest.raises(ValueError):
        enum("valor-que-no-existe")


@pytest.mark.regression
def test_status_values_are_the_stable_strings_stored_in_the_database() -> None:
    assert {s.value for s in ReviewStatus} == {"completed", "failed"}
    assert {s.value for s in ChangeStatus} == {"pending"}
