"""El mensaje que escribe `git revert` de verdad es el que reconoce `parse_reverted_sha`."""

from __future__ import annotations

from pathlib import Path

from duelo.domain.commit_state import parse_reverted_sha
from tests.unit.adapters.git.helpers import commit_file, git, init_repo


def _last_message(repo: Path) -> tuple[str, str]:
    title, _, body = git(repo, "log", "-1", "--format=%s%x00%b").partition("\x00")
    return title, body


def test_the_message_of_a_real_git_revert_is_accepted(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    commit_file(repo, "a.txt", "1\n", "uno")
    target = commit_file(repo, "b.txt", "2\n", "feat: login")
    git(repo, "revert", "--no-edit", "HEAD")
    title, _, body = git(repo, "log", "-1", "--format=%s%x00%b").partition("\x00")

    assert parse_reverted_sha(title, body) == target


def test_reapplying_a_revert_is_accepted(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "r")
    commit_file(repo, "a.txt", "1\n", "uno")
    commit_file(repo, "b.txt", "2\n", "feat: login")
    git(repo, "revert", "--no-edit", "HEAD")
    reverted_revert = git(repo, "rev-parse", "HEAD").strip()
    git(repo, "revert", "--no-edit", "HEAD")
    title, _, body = git(repo, "log", "-1", "--format=%s%x00%b").partition("\x00")

    assert title.startswith(("Revert", "Reapply"))
    assert parse_reverted_sha(title, body) == reverted_revert
