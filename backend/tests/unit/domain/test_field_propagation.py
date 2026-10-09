"""Cada dato de entrada debe acabar, tal cual, en la entidad (mata mutantes de reenvío)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from duelo.domain.change import Change, ChangeKind
from duelo.domain.review import Finding, Review, ReviewResult

CREATED_AT = datetime(2026, 10, 9, 12, 30, 45, tzinfo=UTC)


def _change_inputs() -> dict[str, object]:
    return {
        "project_id": uuid4(),
        "kind": ChangeKind.PR,
        "ref": "refs/pull/7/head",
        "head_sha": "c0ffee" * 6,
        "title": "feat: titulo distinto",
        "author": "autor-distinto",
        "url": "https://example.com/pull/7",
        "diff": "diff --git a/distinto b/distinto",
        "diff_truncated": True,
        "created_at": CREATED_AT,
    }


@pytest.mark.parametrize("field", list(_change_inputs()))
def test_change_new_keeps_every_input_field(field: str) -> None:
    inputs = _change_inputs()

    change = Change.new(**inputs)  # type: ignore[arg-type]

    assert getattr(change, field) == inputs[field]


def test_change_new_generates_a_distinct_uuid_each_time() -> None:
    inputs = _change_inputs()

    first, second = Change.new(**inputs), Change.new(**inputs)  # type: ignore[arg-type]

    assert isinstance(first.id, UUID)
    assert first.id != second.id


def _review_extras() -> dict[str, object]:
    return {
        "change_id": uuid4(),
        "agent": "agent_x",
        "run": 3,
        "duration_ms": 1234,
        "created_at": CREATED_AT,
    }


RESULT = ReviewResult(
    summary="resumen",
    score=7,
    findings=(Finding("bug", "a.py", 12, "mensaje"),),
)


@pytest.mark.parametrize("field", list(_review_extras()))
def test_review_succeeded_keeps_every_input_field(field: str) -> None:
    extras = _review_extras()

    review = Review.succeeded(**extras, result=RESULT, raw_output="salida cruda")  # type: ignore[arg-type]

    assert getattr(review, field) == extras[field]


def test_review_succeeded_keeps_the_result_and_raw_output() -> None:
    review = Review.succeeded(**_review_extras(), result=RESULT, raw_output="salida cruda")  # type: ignore[arg-type]

    assert review.raw_output == "salida cruda"
    assert (review.summary, review.score, review.findings) == (
        "resumen",
        7,
        (Finding("bug", "a.py", 12, "mensaje"),),
    )


@pytest.mark.parametrize("field", list(_review_extras()))
def test_review_failed_keeps_every_input_field(field: str) -> None:
    extras = _review_extras()

    review = Review.failed(**extras, error="timeout")  # type: ignore[arg-type]

    assert getattr(review, field) == extras[field]
    assert review.error == "timeout"


def test_review_failed_allows_unknown_duration() -> None:
    extras = _review_extras() | {"duration_ms": None}

    assert Review.failed(**extras, error="x").duration_ms is None  # type: ignore[arg-type]


def test_each_review_gets_a_distinct_uuid() -> None:
    extras = _review_extras()

    ids = {
        Review.succeeded(**extras, result=RESULT, raw_output=None).id,  # type: ignore[arg-type]
        Review.succeeded(**extras, result=RESULT, raw_output=None).id,  # type: ignore[arg-type]
        Review.failed(**extras, error="x").id,  # type: ignore[arg-type]
    }

    assert len(ids) == 3
    assert all(isinstance(i, UUID) for i in ids)
