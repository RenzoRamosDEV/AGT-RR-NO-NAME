"""Decisión de reutilizar las reviews de un commit en la PR con el mismo SHA y diff."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ReviewReused
from duelo.domain.review import Finding, Review, ReviewResult, ReviewStatus
from duelo.domain.review_reuse import reviews_to_reuse

NOW = datetime(2026, 1, 2, tzinfo=UTC)
LATER = datetime(2026, 1, 3, tzinfo=UTC)
AGENTS = ("claude", "codex")
DIFF = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x\n+y\n"
PROJECT = uuid4()


def _change(kind: ChangeKind, *, diff: str = DIFF, sha: str = "a" * 40, **kw: object) -> Change:
    return replace(
        Change.new(
            project_id=PROJECT,
            kind=kind,
            ref="main",
            head_sha=sha,
            title="t",
            author="a",
            url="",
            diff=diff,
            diff_truncated=False,
            created_at=NOW,
        ),
        **kw,
    )


def _done(change: Change, agent: str, *, run: int | None = None) -> Review:
    return Review.succeeded(
        change_id=change.id,
        agent=agent,
        run=run or change.run,
        result=ReviewResult(
            summary=f"resumen de {agent}",
            score=7,
            findings=(Finding(severity="bug", file="a.py", line=1, message="falla"),),
        ),
        raw_output="salida cruda que no se copia",
        duration_ms=1234,
        created_at=NOW,
    )


def _failed(change: Change, agent: str) -> Review:
    return Review.failed(
        change_id=change.id,
        agent=agent,
        run=change.run,
        error="caído",
        duration_ms=5,
        created_at=NOW,
    )


def _decide(pr: Change, commit: Change | None, reviews: list[Review]) -> tuple[Review, ...]:
    return reviews_to_reuse(pr, commit, reviews, agent_names=AGENTS, now=LATER)


def test_a_pr_with_the_same_sha_and_diff_reuses_the_review_of_every_agent() -> None:
    commit, pr = _change(ChangeKind.COMMIT), _change(ChangeKind.PR)

    copies = _decide(pr, commit, [_done(commit, "codex"), _done(commit, "claude")])

    assert [c.agent for c in copies] == ["claude", "codex"]
    for copy in copies:
        assert copy.change_id == pr.id
        assert copy.reused_from_change_id == commit.id
        assert copy.run == 1 and copy.status is ReviewStatus.COMPLETED
        assert copy.created_at == LATER
        assert (copy.score, copy.duration_ms) == (7, 1234)
        assert copy.summary == f"resumen de {copy.agent}"
        assert copy.findings == (Finding("bug", "a.py", 1, "falla"),)
        assert copy.raw_output is None and copy.error is None


def test_each_copy_is_a_new_review_not_the_original() -> None:
    commit, pr = _change(ChangeKind.COMMIT), _change(ChangeKind.PR)
    originals = [_done(commit, "claude"), _done(commit, "codex")]

    copies = _decide(pr, commit, originals)

    assert all(isinstance(c.id, UUID) for c in copies)
    assert len({c.id for c in copies}) == 2
    assert {c.id for c in copies}.isdisjoint({o.id for o in originals})


@pytest.mark.parametrize(
    ("label", "commit_kw", "pr_kw"),
    [
        ("diff distinto", {}, {"diff": DIFF + "+otro\n"}),
        ("SHA distinto", {"sha": "b" * 40}, {}),
        ("diff truncado distinto", {}, {"diff_truncated": True}),
        ("otro proyecto", {"project_id": uuid4()}, {}),
    ],
)
def test_nothing_is_reused_when_the_pr_is_not_the_same_code(
    label: str, commit_kw: dict[str, object], pr_kw: dict[str, object]
) -> None:
    # No se tocan los diccionarios de los parámetros: mutmut ejecuta la suite varias veces en el
    # mismo proceso y la segunda pasada los vería ya modificados.
    commit = _change(ChangeKind.COMMIT, **commit_kw)
    pr = _change(ChangeKind.PR, **pr_kw)

    assert _decide(pr, commit, [_done(commit, "claude"), _done(commit, "codex")]) == (), label


def test_nothing_is_reused_without_a_commit() -> None:
    pr = _change(ChangeKind.PR)

    assert _decide(pr, None, []) == ()


def test_a_commit_never_reuses_another_commit_and_a_pr_never_reuses_a_pr() -> None:
    commit = _change(ChangeKind.COMMIT)
    other_commit = _change(ChangeKind.COMMIT)
    pr = _change(ChangeKind.PR)
    reviews = [_done(commit, "claude"), _done(commit, "codex")]

    assert _decide(other_commit, commit, reviews) == ()
    assert _decide(pr, replace(commit, kind=ChangeKind.PR), reviews) == ()


def test_nothing_is_reused_when_an_expected_agent_is_missing() -> None:
    commit, pr = _change(ChangeKind.COMMIT), _change(ChangeKind.PR)

    assert _decide(pr, commit, [_done(commit, "claude")]) == ()


def test_nothing_is_reused_when_an_agent_failed() -> None:
    commit, pr = _change(ChangeKind.COMMIT), _change(ChangeKind.PR)

    assert _decide(pr, commit, [_done(commit, "claude"), _failed(commit, "codex")]) == ()


def test_only_the_current_run_of_the_commit_counts() -> None:
    commit = _change(ChangeKind.COMMIT, run=2)
    pr = _change(ChangeKind.PR)
    old = [_done(commit, "claude", run=1), _done(commit, "codex", run=1)]

    assert _decide(pr, commit, old) == ()
    current = [_done(commit, "claude", run=2), _done(commit, "codex", run=2)]
    assert len(_decide(pr, commit, current)) == 2


def test_reviews_of_agents_that_are_not_expected_are_ignored() -> None:
    commit, pr = _change(ChangeKind.COMMIT), _change(ChangeKind.PR)
    reviews = [_done(commit, "claude"), _done(commit, "codex"), _done(commit, "agent_1")]

    copies = _decide(pr, commit, reviews)

    assert [c.agent for c in copies] == ["claude", "codex"]


def test_agent_names_are_compared_exactly() -> None:
    commit, pr = _change(ChangeKind.COMMIT), _change(ChangeKind.PR)

    assert _decide(pr, commit, [_done(commit, "Claude"), _done(commit, "Codex")]) == ()


def test_nothing_is_reused_when_no_agent_is_expected() -> None:
    commit, pr = _change(ChangeKind.COMMIT), _change(ChangeKind.PR)

    assert reviews_to_reuse(pr, commit, [], agent_names=(), now=LATER) == ()


def test_a_failed_review_cannot_be_copied() -> None:
    commit = _change(ChangeKind.COMMIT)

    with pytest.raises(ValueError, match="^solo se reutilizan reviews completadas$"):
        Review.reused_from(_failed(commit, "claude"), change_id=uuid4(), created_at=LATER)


def test_the_reuse_event_names_the_review_the_agent_and_where_it_was_copied_from() -> None:
    commit = _change(ChangeKind.COMMIT)
    copy = Review.reused_from(_done(commit, "claude"), change_id=uuid4(), created_at=LATER)

    event = ReviewReused.of(copy, project_id=PROJECT)

    assert event.type == "review.reused"
    assert event.to_payload() == {
        "review_id": str(copy.id),
        "change_id": str(copy.change_id),
        "project_id": str(PROJECT),
        "agent": "claude",
        "reused_from_change_id": str(commit.id),
    }


def test_the_reuse_event_cannot_be_built_for_a_review_the_agent_made_itself() -> None:
    commit = _change(ChangeKind.COMMIT)

    with pytest.raises(ValueError, match="^la review no es una copia: no tiene change de origen$"):
        ReviewReused.of(_done(commit, "claude"), project_id=PROJECT)
