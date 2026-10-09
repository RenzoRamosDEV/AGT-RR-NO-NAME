"""Estado agregado de las reviews de un change y normalización de severidades."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from duelo.domain.review import Review, ReviewResult
from duelo.domain.review_status import (
    RETRYABLE_STATUSES,
    ChangeReviewStatus,
    Severity,
    normalize_severity,
    review_status_from_counts,
    review_status_of_run,
    summarize_severities,
)

P, R, F, X, C = (
    ChangeReviewStatus.PENDING,
    ChangeReviewStatus.RUNNING,
    ChangeReviewStatus.FAILED,
    ChangeReviewStatus.PARTIAL_FAILED,
    ChangeReviewStatus.COMPLETED,
)


@pytest.mark.parametrize(
    ("completed", "failed", "expected", "status"),
    [
        # Tabla de decisión con dos agentes esperados.
        (0, 0, 2, P),
        (1, 0, 2, R),
        (0, 1, 2, R),  # un fallo no cierra el estado mientras otro agente puede completarse
        (2, 0, 2, C),
        (0, 2, 2, F),
        (1, 1, 2, X),
        # Un solo agente: el primer resultado ya es el final.
        (1, 0, 1, C),
        (0, 1, 1, F),
        # Valores límite: más reviews que agentes esperados (configuración que cambió).
        (3, 0, 2, C),
        (1, 2, 2, X),
        (0, 3, 2, F),
    ],
)
def test_status_decision_table(completed: int, failed: int, expected: int, status: object) -> None:
    assert (
        review_status_from_counts(completed=completed, failed=failed, expected_agents=expected)
        is status
    )


@given(
    completed=st.integers(0, 6),
    failed=st.integers(0, 6),
    expected=st.integers(1, 6),
)
def test_status_is_final_only_once_every_expected_review_is_registered(
    completed: int, failed: int, expected: int
) -> None:
    status = review_status_from_counts(completed=completed, failed=failed, expected_agents=expected)

    registered = completed + failed
    assert (status in {P, R}) == (registered < expected)
    assert (status is P) == (registered == 0)
    if registered >= expected:
        assert (status is C) == (failed == 0)
        assert (status is F) == (completed == 0)


def test_only_finished_executions_with_failures_are_retryable() -> None:
    assert RETRYABLE_STATUSES == {F, X}


def _review(*, run: int, agent: str, fail: bool) -> Review:
    common = {"change_id": uuid4(), "agent": agent, "run": run, "created_at": datetime.now(UTC)}
    if fail:
        return Review.failed(error="boom", duration_ms=None, **common)
    return Review.succeeded(
        result=ReviewResult(summary="ok", score=5), raw_output=None, duration_ms=1, **common
    )


def test_status_of_run_ignores_reviews_of_other_runs() -> None:
    reviews = [
        _review(run=1, agent="a", fail=True),
        _review(run=1, agent="b", fail=True),
        _review(run=2, agent="a", fail=False),
    ]

    assert review_status_of_run(1, reviews, expected_agents=2) is F
    assert review_status_of_run(2, reviews, expected_agents=2) is R
    assert review_status_of_run(3, reviews, expected_agents=2) is P


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("bug", Severity.BUG),
        ("  BUG ", Severity.BUG),
        ("Critical", Severity.BUG),
        ("risk", Severity.RISK),
        ("Warning", Severity.RISK),
        ("improvement", Severity.IMPROVEMENT),
        ("suggestion", Severity.IMPROVEMENT),
        ("nit", Severity.NIT),
        ("style", Severity.NIT),
        ("banana", Severity.OTHER),
        ("", Severity.OTHER),
        ("N/A", Severity.OTHER),
    ],
)
def test_severity_is_normalized_on_read(raw: str, expected: Severity) -> None:
    assert normalize_severity(raw) is expected


def test_every_documented_severity_maps_to_itself() -> None:
    # docs/spec/duelo.md: "bug|risk|improvement|nit"; el contrato con los agentes no puede
    # acabar en `other` por un cambio en la tabla de sinónimos.
    for value in ("bug", "risk", "improvement", "nit"):
        assert normalize_severity(value).value == value


def test_summary_counts_each_bucket_and_the_total() -> None:
    summary = summarize_severities(["bug", "Risk", "nit", "nit", "banana", "suggestion"])

    assert (summary.total, summary.bug, summary.risk, summary.improvement, summary.nit) == (
        6,
        1,
        1,
        1,
        2,
    )
    assert summary.other == 1


def test_summary_of_nothing_is_all_zeros() -> None:
    summary = summarize_severities([])

    assert (summary.total, summary.bug, summary.risk, summary.improvement) == (0, 0, 0, 0)
    assert (summary.nit, summary.other) == (0, 0)


@given(st.lists(st.text(max_size=12), max_size=30))
def test_summary_buckets_always_add_up_to_the_total(raw: list[str]) -> None:
    s = summarize_severities(raw)

    assert s.total == len(raw) == s.bug + s.risk + s.improvement + s.nit + s.other
