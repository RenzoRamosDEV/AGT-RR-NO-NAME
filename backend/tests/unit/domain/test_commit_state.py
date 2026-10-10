"""Reglas puras del estado de un commit: activo, deshecho o revertido, la lectura de
`This reverts commit <sha>` y la decisión del barrido de alcanzabilidad."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from duelo.domain.change import Change, ChangeKind
from duelo.domain.commit_state import (
    CommitState,
    Reachability,
    TrackedCommit,
    commit_state_of,
    decide_reachability,
    is_safe_sha_argument,
    parse_reverted_sha,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40


def _tracked(
    sha: str, *, created_at: datetime = T0, discarded: bool = False, id: UUID | None = None
) -> TrackedCommit:
    return TrackedCommit(id=id or uuid4(), head_sha=sha, created_at=created_at, discarded=discarded)


def _complete(*shas: str) -> Reachability:
    return Reachability(shas=frozenset(shas), truncated=False)


def _truncated(*shas: str, oldest_at: datetime | None = T0) -> Reachability:
    return Reachability(shas=frozenset(shas), truncated=True, oldest_at=oldest_at)


# --- commit_state_of -----------------------------------------------------------------------


def test_a_commit_without_marks_is_active() -> None:
    state = commit_state_of(kind=ChangeKind.COMMIT, discarded_at=None, reverted=False)

    assert state is CommitState.ACTIVE


def test_a_discarded_commit_is_discarded() -> None:
    state = commit_state_of(kind=ChangeKind.COMMIT, discarded_at=T0, reverted=False)

    assert state is CommitState.DISCARDED


def test_a_commit_with_a_live_revert_is_reverted() -> None:
    state = commit_state_of(kind=ChangeKind.COMMIT, discarded_at=None, reverted=True)

    assert state is CommitState.REVERTED


def test_discarded_wins_over_reverted() -> None:
    """Un commit que ya no está en la rama no puede seguir en ella «revertido»."""
    state = commit_state_of(kind=ChangeKind.COMMIT, discarded_at=T0, reverted=True)

    assert state is CommitState.DISCARDED


@pytest.mark.parametrize("discarded_at", [None, T0])
@pytest.mark.parametrize("reverted", [False, True])
def test_a_pr_is_always_active(discarded_at: datetime | None, reverted: bool) -> None:
    state = commit_state_of(kind=ChangeKind.PR, discarded_at=discarded_at, reverted=reverted)

    assert state is CommitState.ACTIVE


# --- parse_reverted_sha --------------------------------------------------------------------


def test_the_sha_of_a_git_revert_message_is_found() -> None:
    body = f"This reverts commit {SHA_A}.\n\nPorque rompe el login."

    assert parse_reverted_sha('Revert "feat: login"', body) == SHA_A


def test_a_revert_of_a_merge_commit_still_gives_the_sha() -> None:
    body = f"This reverts commit {SHA_A}, reversing\nchanges made to {SHA_B}."

    assert parse_reverted_sha("", body) == SHA_A


def test_an_abbreviated_sha_written_by_hand_is_accepted() -> None:
    assert parse_reverted_sha("", "This reverts commit abc1234") == "abc1234"


def test_the_sha_is_returned_in_lowercase() -> None:
    assert parse_reverted_sha("", f"This reverts commit {SHA_A.upper()}") == SHA_A


def test_the_title_is_read_too() -> None:
    assert parse_reverted_sha(f"This reverts commit {SHA_B}", "") == SHA_B


def test_the_first_text_with_a_sha_wins() -> None:
    first = f"This reverts commit {SHA_A}"
    second = f"This reverts commit {SHA_B}"

    assert parse_reverted_sha(first, second) == SHA_A


@pytest.mark.parametrize(
    "text",
    [
        "",
        "feat: algo",
        'Revert "feat: login"',  # sin el cuerpo no dice qué SHA revierte
        "This reverts commit",
        "This reverts commit xyz1234",
        "This reverts commit abc12",  # demasiado corto
        "this reverts commit abc1234",  # git lo escribe con mayúscula inicial
    ],
)
def test_a_message_without_a_revert_gives_none(text: str) -> None:
    assert parse_reverted_sha(text, text) is None


# --- is_safe_sha_argument ------------------------------------------------------------------


@pytest.mark.parametrize("sha", [SHA_A, "abc1234", "ABCDEF0123456789", "f" * 64])
def test_a_hexadecimal_sha_is_a_safe_argument(sha: str) -> None:
    assert is_safe_sha_argument(sha)


@pytest.mark.parametrize(
    "sha",
    [
        "",
        "abc12",  # demasiado corto
        "a" * 65,
        "--all",
        "-n1",
        "--output=/tmp/x",
        "abc1234;rm -rf",
        "abc 1234",
        "abc1234\n",
        "main",
        "HEAD~1",
        "abc123g",
    ],
)
def test_anything_else_is_not_a_safe_argument(sha: str) -> None:
    """El SHA guardado viene de la ingesta y nunca debe poder ser una opción de git."""
    assert not is_safe_sha_argument(sha)


# --- decide_reachability: conjunto completo -------------------------------------------------


def test_with_a_complete_set_a_missing_commit_is_discarded() -> None:
    lost, kept = _tracked(SHA_A), _tracked(SHA_B)

    decision = decide_reachability([lost, kept], _complete(SHA_B))

    assert decision.discard == (lost,)
    assert decision.restore == ()
    assert decision.confirm_individually is False


def test_a_discarded_commit_that_is_reachable_again_is_restored() -> None:
    back = _tracked(SHA_A, discarded=True)

    decision = decide_reachability([back], _complete(SHA_A))

    assert decision.restore == (back,)
    assert decision.discard == ()


def test_an_already_discarded_commit_that_is_still_missing_is_left_alone() -> None:
    decision = decide_reachability([_tracked(SHA_A, discarded=True)], _complete(SHA_B))

    assert decision.discard == ()
    assert decision.restore == ()


def test_a_reachable_active_commit_is_left_alone() -> None:
    decision = decide_reachability([_tracked(SHA_A)], _complete(SHA_A))

    assert decision.discard == ()
    assert decision.restore == ()


def test_shas_are_compared_in_lowercase_and_ignoring_spaces() -> None:
    decision = decide_reachability([_tracked(f" {SHA_A.upper()} ")], _complete(SHA_A))

    assert decision.discard == ()


def test_an_empty_repository_discards_every_active_commit() -> None:
    commits = [_tracked(SHA_A), _tracked(SHA_B)]

    decision = decide_reachability(commits, _complete())

    assert decision.discard == tuple(commits)


# --- decide_reachability: ventana llena ------------------------------------------------------


def test_with_a_truncated_set_older_changes_are_not_evaluated() -> None:
    """Un commit anterior a la ventana puede ser alcanzable aunque git no lo haya listado."""
    window_start = T0 + timedelta(days=10)
    old = _tracked(SHA_A, created_at=T0)

    decision = decide_reachability([old], _truncated(SHA_B, oldest_at=window_start))

    assert decision.discard == ()


def test_with_a_truncated_set_a_recent_missing_commit_needs_confirmation() -> None:
    window_start = T0 + timedelta(days=10)
    recent = _tracked(SHA_A, created_at=window_start + timedelta(hours=1))

    decision = decide_reachability([recent], _truncated(SHA_B, oldest_at=window_start))

    assert decision.discard == (recent,)
    assert decision.confirm_individually is True


def test_a_change_created_exactly_at_the_window_start_is_evaluated() -> None:
    window_start = T0 + timedelta(days=10)
    edge = _tracked(SHA_A, created_at=window_start)

    decision = decide_reachability([edge], _truncated(SHA_B, oldest_at=window_start))

    assert decision.discard == (edge,)


def test_with_a_truncated_set_without_a_window_start_nothing_is_discarded() -> None:
    decision = decide_reachability([_tracked(SHA_A)], _truncated(oldest_at=None))

    assert decision.discard == ()


def test_with_a_truncated_set_restoring_only_needs_the_sha_to_be_listed() -> None:
    window_start = T0 + timedelta(days=10)
    old_and_back = _tracked(SHA_A, created_at=T0, discarded=True)

    decision = decide_reachability([old_and_back], _truncated(SHA_A, oldest_at=window_start))

    assert decision.restore == (old_and_back,)


# --- decide_reachability: cada caso deja seguir con los demás commits ---------------------------


def test_a_commit_that_is_left_alone_does_not_stop_the_ones_after_it() -> None:
    """El bucle debe seguir tras cada commit que no cambia: el perdido va DESPUÉS de uno alcanzable,
    de uno ya deshecho que sigue perdido y de uno anterior a la ventana."""
    kept = _tracked(SHA_A)
    still_lost = _tracked(SHA_B, discarded=True)
    window_start = T0 + timedelta(days=10)
    too_old = _tracked(SHA_C, created_at=T0)
    lost = _tracked("d" * 40, created_at=window_start + timedelta(hours=1))

    decision = decide_reachability(
        [kept, still_lost, too_old, lost], _truncated(SHA_A, oldest_at=window_start)
    )

    assert decision.discard == (lost,)
    assert decision.restore == ()


def test_a_restored_commit_does_not_stop_the_ones_after_it() -> None:
    back = _tracked(SHA_A, discarded=True)
    lost = _tracked(SHA_B)

    decision = decide_reachability([back, lost], _complete(SHA_A))

    assert decision.restore == (back,)
    assert decision.discard == (lost,)


# --- Change.new y los commits de revert --------------------------------------------------------


def _new_change(kind: ChangeKind, reverts_sha: str | None) -> Change:
    return Change.new(
        project_id=uuid4(),
        kind=kind,
        ref="main",
        head_sha=SHA_B,
        title="t",
        author="a",
        url="",
        diff="",
        diff_truncated=False,
        created_at=T0,
        reverts_sha=reverts_sha,
    )


def test_a_commit_keeps_the_sha_it_reverts() -> None:
    assert _new_change(ChangeKind.COMMIT, SHA_A).reverts_sha == SHA_A


def test_a_pr_never_keeps_a_sha_it_reverts() -> None:
    assert _new_change(ChangeKind.PR, SHA_A).reverts_sha is None


def test_a_new_change_is_not_discarded() -> None:
    assert _new_change(ChangeKind.COMMIT, None).discarded_at is None


# --- propiedad -----------------------------------------------------------------------------

_SHAS = st.sampled_from([SHA_A, SHA_B, SHA_C, "d" * 40, "e" * 40])


@given(
    tracked=st.lists(
        st.builds(
            _tracked,
            _SHAS,
            created_at=st.datetimes(
                min_value=datetime(2025, 1, 1),
                max_value=datetime(2027, 1, 1),
                timezones=st.just(UTC),
            ),
            discarded=st.booleans(),
        ),
        max_size=8,
    ),
    reachable=st.frozensets(_SHAS),
    truncated=st.booleans(),
)
def test_the_decision_never_discards_a_reachable_commit_nor_restores_a_missing_one(
    tracked: list[TrackedCommit], reachable: frozenset[str], truncated: bool
) -> None:
    reachability = Reachability(shas=reachable, truncated=truncated, oldest_at=T0)

    decision = decide_reachability(tracked, reachability)

    assert all(c.head_sha not in reachable and not c.discarded for c in decision.discard)
    assert all(c.head_sha in reachable and c.discarded for c in decision.restore)
    assert set(decision.discard).isdisjoint(decision.restore)
    assert decision.confirm_individually is truncated
