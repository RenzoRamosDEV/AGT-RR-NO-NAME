from __future__ import annotations

import pytest

from duelo.adapters.agents.codex_cli import (
    DISABLED_FEATURES,
    REVIEWED_ALLOWED_FEATURES,
    unreviewed_features,
)

# El formato real de `codex features list`: nombre, etapa (puede llevar espacios) y si está activa.
LISTING = """\
shell_tool                               stable             true
unified_exec_tty                         stable             true
sleep_tool                               stable             true
code_mode                                under development  false
instant_interrupt                        under development  true
steer                                    removed            true
brand_new_tool                           stable             true
another_new_one                          under development  true
disabled_new_tool                        stable             false
"""


def test_an_enabled_feature_in_neither_list_is_reported() -> None:
    assert unreviewed_features(LISTING) == ["another_new_one", "brand_new_tool"]


def test_classified_removed_and_disabled_features_are_not_reported() -> None:
    quiet = """\
shell_tool                               stable             true
sleep_tool                               stable             true
steer                                    removed            true
unknown_but_removed                      removed            true
unknown_but_disabled                     stable             false
"""
    assert unreviewed_features(quiet) == []


def test_a_stage_with_spaces_is_parsed() -> None:
    assert unreviewed_features("mystery_tool   under development   true") == ["mystery_tool"]


@pytest.mark.parametrize("noise", ["", "\n\n", "Features:", "just text here", "name only"])
def test_lines_that_are_not_features_are_ignored(noise: str) -> None:
    assert unreviewed_features(noise) == []


def test_the_result_is_sorted_and_has_no_duplicates() -> None:
    listing = "zeta stable true\nalpha stable true\nzeta stable true\n"

    assert unreviewed_features(listing) == ["alpha", "zeta"]


def test_a_feature_that_is_denied_or_allowed_is_never_reported_whatever_its_stage() -> None:
    denied, allowed = DISABLED_FEATURES[0], next(iter(REVIEWED_ALLOWED_FEATURES))
    listing = f"{denied} experimental true\n{allowed} under development true\n"

    assert unreviewed_features(listing) == []


@pytest.mark.regression
def test_the_features_the_review_pointed_out_are_disabled() -> None:
    """Origen: la segunda revisión de Codex vio activas funciones que la lista no cubría."""
    reported = {
        "unified_exec_tty",
        "shell_snapshot",
        "multi_agent",
        "skill_mcp_dependency_install",
        "workspace_dependencies",
        "shell_tool",
        "unified_exec",
        "hooks",
        "view_image",
        "code_mode_host",
        "worktrees",
        "plugins",
        "remote_plugin",
        "tool_suggest",
    }

    assert reported <= set(DISABLED_FEATURES)


def test_the_two_lists_are_consistent() -> None:
    assert len(DISABLED_FEATURES) == len(set(DISABLED_FEATURES))  # sin repetidos
    assert set(DISABLED_FEATURES).isdisjoint(REVIEWED_ALLOWED_FEATURES)  # ninguna en las dos
    assert all(reason.strip() for reason in REVIEWED_ALLOWED_FEATURES.values())  # con su motivo


def test_nothing_that_runs_commands_or_reads_the_disk_is_allowed() -> None:
    dangerous = ("shell", "exec", "view_image", "worktree", "workspace", "plugin", "multi_agent")

    assert not [name for name in REVIEWED_ALLOWED_FEATURES if any(d in name for d in dangerous)]
