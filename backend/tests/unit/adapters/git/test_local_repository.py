from __future__ import annotations

import os
from pathlib import Path

import pytest

from duelo.adapters.git import local_repository
from duelo.adapters.git.local_repository import MAX_PATH, LocalGitRepository
from duelo.adapters.subprocess_runner import CommandTimeout
from duelo.application.ports import InvalidRepository
from tests.unit.adapters.git.helpers import commit_file, git, init_repo


async def test_the_root_of_a_repo_with_a_github_origin(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "widgets", origin="git@github.com:acme/widgets.git")

    info = await LocalGitRepository().inspect(str(repo))

    assert (info.root, info.remote_url) == (str(repo), "git@github.com:acme/widgets.git")


async def test_a_repo_without_origin_has_no_remote(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "widgets")

    assert (await LocalGitRepository().inspect(str(repo))).remote_url is None


async def test_a_linked_worktree_root_is_accepted(tmp_path: Path) -> None:
    main = init_repo(tmp_path / "main")
    commit_file(main)
    git(main, "worktree", "add", "-q", str(tmp_path / "wt"), "-b", "otra")

    info = await LocalGitRepository().inspect(str(tmp_path / "wt"))

    assert info.root == str((tmp_path / "wt").resolve())


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("", "no es válida"),
        ("a\x00b", "no es válida"),
        ("relativa/repo", "absoluta"),
        ("x" * (MAX_PATH + 1), "demasiado larga"),
    ],
)
async def test_malformed_paths_are_rejected_before_touching_git(path: str, message: str) -> None:
    with pytest.raises(InvalidRepository, match=message):
        await LocalGitRepository().inspect(path)


async def test_dot_dot_segments_are_rejected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "widgets")

    with pytest.raises(InvalidRepository, match=r"\.\."):
        await LocalGitRepository().inspect(f"{repo}/../widgets")


async def test_a_missing_path_and_a_file_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "fichero").write_text("x")

    with pytest.raises(InvalidRepository, match="no existe"):
        await LocalGitRepository().inspect(str(tmp_path / "nada"))
    with pytest.raises(InvalidRepository, match="no es una carpeta"):
        await LocalGitRepository().inspect(str(tmp_path / "fichero"))


async def test_a_symlink_to_a_repo_is_rejected(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "real")
    link = tmp_path / "enlace"
    os.symlink(repo, link)

    with pytest.raises(InvalidRepository, match="enlace simbólico"):
        await LocalGitRepository().inspect(str(link))


async def test_a_subfolder_of_a_repo_is_not_its_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "widgets")
    (repo / "src").mkdir()

    with pytest.raises(InvalidRepository, match="raíz"):
        await LocalGitRepository().inspect(str(repo / "src"))


async def test_a_plain_folder_is_not_a_repo(tmp_path: Path) -> None:
    (tmp_path / "suelta").mkdir()

    with pytest.raises(InvalidRepository, match="no es un repositorio"):
        await LocalGitRepository().inspect(str(tmp_path / "suelta"))


async def test_a_missing_git_binary_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "widgets")
    monkeypatch.setenv("PATH", str(tmp_path / "vacio"))

    with pytest.raises(InvalidRepository, match="git no está instalado"):
        await LocalGitRepository().inspect(str(repo))


async def test_a_git_that_hangs_is_reported_as_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "widgets")

    async def hang(*_: object, **__: object) -> None:
        raise CommandTimeout("git")

    monkeypatch.setattr(local_repository, "run_command", hang)

    with pytest.raises(InvalidRepository, match="no respondió a tiempo"):
        await LocalGitRepository().inspect(str(repo))


async def test_a_git_that_hangs_reading_origin_just_means_no_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "widgets", origin="git@github.com:acme/widgets.git")
    real = local_repository.run_command

    async def hang_on_config(argv: list[str], **kwargs: object):  # type: ignore[no-untyped-def]
        if "config" in argv:
            raise CommandTimeout("git")
        return await real(argv, **kwargs)

    monkeypatch.setattr(local_repository, "run_command", hang_on_config)

    assert (await LocalGitRepository().inspect(str(repo))).remote_url is None
