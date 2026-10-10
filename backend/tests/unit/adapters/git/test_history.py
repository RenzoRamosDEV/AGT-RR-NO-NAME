"""El historial de un repositorio real: qué commits son alcanzables tras `reset`, `amend`, borrar
ramas, cabezas desacopladas y etiquetas, y cómo falla cuando no se puede consultar."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from duelo.adapters.git import history as history_module
from duelo.adapters.git.history import LocalGitHistory
from duelo.adapters.subprocess_runner import CommandNotFound, CommandTimeout
from duelo.application.ports import HistoryUnavailable
from tests.unit.adapters.git.helpers import commit_file, git, init_repo

WINDOW = 5000


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return init_repo(tmp_path / "widgets")


def sha_of(repo: Path, rev: str = "HEAD") -> str:
    return git(repo, "rev-parse", rev).strip()


# --- reachable --------------------------------------------------------------------------------


async def test_every_commit_of_the_current_branch_is_reachable(repo: Path) -> None:
    first = commit_file(repo, "a.txt", "1\n", "uno")
    second = commit_file(repo, "b.txt", "2\n", "dos")

    reach = await LocalGitHistory().reachable(str(repo), limit=WINDOW)

    assert reach.shas == {first, second}
    assert reach.truncated is False


async def test_a_reset_makes_the_commit_unreachable(repo: Path) -> None:
    commit_file(repo, "a.txt", "1\n", "uno")
    lost = commit_file(repo, "b.txt", "2\n", "dos")
    git(repo, "reset", "--hard", "-q", "HEAD~1")

    reach = await LocalGitHistory().reachable(str(repo), limit=WINDOW)

    assert lost not in reach.shas


async def test_an_amend_makes_the_old_commit_unreachable_and_the_new_one_reachable(
    repo: Path,
) -> None:
    old = commit_file(repo, "a.txt", "1\n", "uno")
    git(repo, "commit", "-q", "--amend", "-m", "uno corregido")
    new = sha_of(repo)

    reach = await LocalGitHistory().reachable(str(repo), limit=WINDOW)

    assert old not in reach.shas
    assert new in reach.shas


async def test_deleting_a_branch_makes_its_exclusive_commits_unreachable(repo: Path) -> None:
    commit_file(repo, "a.txt", "1\n", "uno")
    git(repo, "checkout", "-q", "-b", "feature")
    only_there = commit_file(repo, "f.txt", "f\n", "en la rama")
    git(repo, "checkout", "-q", "main")
    assert only_there in (await LocalGitHistory().reachable(str(repo), limit=WINDOW)).shas

    git(repo, "branch", "-D", "feature", "-q")

    assert only_there not in (await LocalGitHistory().reachable(str(repo), limit=WINDOW)).shas


async def test_a_commit_on_a_detached_head_is_still_reachable(repo: Path) -> None:
    """`--all` incluye `HEAD`: un commit en cabeza desacoplada (o en medio de un rebase) no se
    da por perdido."""
    base = commit_file(repo, "a.txt", "1\n", "uno")
    git(repo, "checkout", "-q", "--detach", base)
    detached = commit_file(repo, "d.txt", "d\n", "en cabeza desacoplada")

    reach = await LocalGitHistory().reachable(str(repo), limit=WINDOW)

    assert detached in reach.shas


async def test_a_commit_only_reachable_from_a_tag_counts(repo: Path) -> None:
    commit_file(repo, "a.txt", "1\n", "uno")
    tagged = commit_file(repo, "b.txt", "2\n", "dos")
    git(repo, "tag", "v1")
    git(repo, "reset", "--hard", "-q", "HEAD~1")

    reach = await LocalGitHistory().reachable(str(repo), limit=WINDOW)

    assert tagged in reach.shas


async def test_a_pushed_commit_stays_reachable_through_the_remote_tracking_ref(
    repo: Path,
) -> None:
    """Tras un push el commit sigue en `origin/<rama>`: no está «deshecho» hasta que se fuerce el
    push. Es el comportamiento documentado del barrido."""
    commit_file(repo, "a.txt", "1\n", "uno")
    pushed = commit_file(repo, "b.txt", "2\n", "dos")
    git(repo, "update-ref", "refs/remotes/origin/main", pushed)
    git(repo, "reset", "--hard", "-q", "HEAD~1")

    reach = await LocalGitHistory().reachable(str(repo), limit=WINDOW)

    assert pushed in reach.shas


async def test_an_empty_repository_has_no_reachable_commits(repo: Path) -> None:
    reach = await LocalGitHistory().reachable(str(repo), limit=WINDOW)

    assert reach.shas == frozenset()
    assert reach.truncated is False
    assert reach.oldest_at is None


async def test_the_window_limits_the_commits_and_flags_the_set_as_truncated(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dates = ["2026-01-01T10:00:00Z", "2026-01-02T10:00:00Z", "2026-01-03T10:00:00Z"]
    shas = []
    for index, date in enumerate(dates):
        monkeypatch.setenv("GIT_COMMITTER_DATE", date)
        shas.append(commit_file(repo, f"f{index}.txt", f"{index}\n", f"commit {index}"))

    reach = await LocalGitHistory().reachable(str(repo), limit=2)

    assert reach.shas == {shas[2], shas[1]}  # los dos más recientes
    assert reach.truncated is True
    assert reach.oldest_at == datetime(2026, 1, 2, 10, 0, tzinfo=UTC)


async def test_a_window_that_exactly_fits_is_flagged_as_truncated_too(repo: Path) -> None:
    """Con tantos commits como el máximo no se puede saber si había más: se trata como lleno."""
    commit_file(repo, "a.txt", "1\n", "uno")
    commit_file(repo, "b.txt", "2\n", "dos")

    reach = await LocalGitHistory().reachable(str(repo), limit=2)

    assert reach.truncated is True


async def test_one_call_to_git_is_enough_for_the_whole_set(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commit_file(repo, "a.txt", "1\n", "uno")
    calls: list[list[str]] = []
    real = history_module.run_command

    async def spy(argv, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(argv))
        return await real(argv, **kwargs)

    monkeypatch.setattr(history_module, "run_command", spy)

    await LocalGitHistory().reachable(str(repo), limit=WINDOW)

    assert len(calls) == 1
    assert calls[0][:3] == ["git", "-C", str(repo)] and "--all" in calls[0]


# --- reachable: fallos -----------------------------------------------------------------------


async def test_a_missing_folder_is_unavailable(tmp_path: Path) -> None:
    with pytest.raises(HistoryUnavailable, match="ya no existe"):
        await LocalGitHistory().reachable(str(tmp_path / "borrada"), limit=WINDOW)


async def test_a_folder_that_is_not_a_repository_is_unavailable(tmp_path: Path) -> None:
    folder = tmp_path / "plain"
    folder.mkdir()

    with pytest.raises(HistoryUnavailable):
        await LocalGitHistory().reachable(str(folder), limit=WINDOW)


async def test_a_corrupt_repository_is_unavailable(repo: Path) -> None:
    commit_file(repo, "a.txt", "1\n", "uno")
    (repo / ".git" / "HEAD").write_text("basura\n")

    with pytest.raises(HistoryUnavailable):
        await LocalGitHistory().reachable(str(repo), limit=WINDOW)


async def test_a_missing_git_binary_is_unavailable(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(*_args: object, **_kwargs: object) -> None:
        raise CommandNotFound("git")

    monkeypatch.setattr(history_module, "run_command", boom)

    with pytest.raises(HistoryUnavailable, match="no está instalado"):
        await LocalGitHistory().reachable(str(repo), limit=WINDOW)


async def test_a_git_that_times_out_is_unavailable(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def slow(*_args: object, **_kwargs: object) -> None:
        raise CommandTimeout("git")

    monkeypatch.setattr(history_module, "run_command", slow)

    with pytest.raises(HistoryUnavailable, match="a tiempo"):
        await LocalGitHistory().reachable(str(repo), limit=WINDOW)


# --- contains ---------------------------------------------------------------------------------


async def test_contains_is_true_for_a_commit_on_a_branch(repo: Path) -> None:
    sha = commit_file(repo, "a.txt", "1\n", "uno")

    assert await LocalGitHistory().contains(str(repo), sha) is True


async def test_contains_accepts_an_abbreviated_and_an_uppercase_sha(repo: Path) -> None:
    sha = commit_file(repo, "a.txt", "1\n", "uno")

    assert await LocalGitHistory().contains(str(repo), sha[:10]) is True
    assert await LocalGitHistory().contains(str(repo), sha.upper()) is True


async def test_contains_is_false_for_a_commit_lost_by_a_reset(repo: Path) -> None:
    """El objeto sigue en el repositorio (reflog) pero ninguna referencia lo alcanza."""
    commit_file(repo, "a.txt", "1\n", "uno")
    lost = commit_file(repo, "b.txt", "2\n", "dos")
    git(repo, "reset", "--hard", "-q", "HEAD~1")

    assert await LocalGitHistory().contains(str(repo), lost) is False


async def test_contains_is_true_for_a_commit_on_a_detached_head(repo: Path) -> None:
    base = commit_file(repo, "a.txt", "1\n", "uno")
    git(repo, "checkout", "-q", "--detach", base)
    detached = commit_file(repo, "d.txt", "d\n", "desacoplado")

    assert await LocalGitHistory().contains(str(repo), detached) is True


async def test_contains_is_false_for_a_sha_that_does_not_exist(repo: Path) -> None:
    commit_file(repo, "a.txt", "1\n", "uno")

    assert await LocalGitHistory().contains(str(repo), "f" * 40) is False


@pytest.mark.parametrize("sha", ["--all", "-n1", "--output=/tmp/x", "main", "HEAD~1", "", "abc12"])
async def test_a_sha_that_is_not_hexadecimal_never_reaches_git(
    repo: Path, monkeypatch: pytest.MonkeyPatch, sha: str
) -> None:
    async def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("no debe llamarse a git con un SHA que no es hexadecimal")

    monkeypatch.setattr(history_module, "run_command", forbidden)

    assert await LocalGitHistory().contains(str(repo), sha) is False
