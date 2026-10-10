from __future__ import annotations

import stat
from pathlib import Path
from uuid import uuid4

import pytest

from duelo.adapters.agents.cli_common import (
    ERROR_TAIL_CHARS,
    CliBadOutput,
    CliFailed,
    CliLoginRequired,
    CliTimeout,
    CliUnavailable,
    looks_like_login_problem,
    private_directory,
    raise_for_failed_command,
    resolve_binary,
    working_directory,
    write_private_file,
)
from duelo.adapters.subprocess_runner import CommandResult
from tests.fakes.cli_runner import FakeProjectPaths, exists


@pytest.mark.parametrize(
    "text",
    [
        "Not logged in · Please run /login",
        "please RUN /LOGIN",
        "codex login required",
        "401 Unauthorized",
    ],
)
def test_login_problems_are_recognised_case_insensitively(text: str) -> None:
    assert looks_like_login_problem(text)


@pytest.mark.parametrize("text", ["", "segmentation fault", "ok"])
def test_other_text_is_not_a_login_problem(text: str) -> None:
    assert not looks_like_login_problem(text)


def test_only_the_tail_of_the_output_is_inspected() -> None:
    """Una transcripción larga que menciona «sign in» al principio no es un problema de sesión."""
    early = "sign in " + "x" * (ERROR_TAIL_CHARS + 50)
    late = "x" * (ERROR_TAIL_CHARS + 50) + " not logged in"

    assert not looks_like_login_problem(early)
    assert looks_like_login_problem(late)


def test_a_failed_command_is_a_login_problem_when_either_stream_says_so() -> None:
    with pytest.raises(CliLoginRequired):
        raise_for_failed_command("Codex", CommandResult(1, "not logged in", ""))
    with pytest.raises(CliLoginRequired):
        raise_for_failed_command("Codex", CommandResult(1, "", "not logged in"))
    with pytest.raises(CliFailed):
        raise_for_failed_command("Codex", CommandResult(7, "x", "y"))


def test_the_error_messages_are_fixed_and_carry_no_output() -> None:
    assert (
        str(CliBadOutput("Codex"))
        == "El CLI de Codex devolvió una respuesta que no cumple el formato"
    )
    assert str(CliTimeout("Codex", 240)) == "El CLI de Codex no respondió en 240 s"
    assert "CODEX_BIN" in str(CliUnavailable("Codex", "CODEX_BIN"))
    assert "sesión" in str(CliLoginRequired("Codex"))
    assert {e.outcome for e in (CliBadOutput("x"), CliTimeout("x", 1), CliFailed("x", 1))} == {
        "bad_output",
        "timeout",
        "failed",
    }


def test_resolve_binary_prefers_the_configured_one_over_the_path(tmp_path: Path) -> None:
    binary = tmp_path / "mi-claude"
    binary.write_text("x")
    binary.chmod(0o755)

    found = resolve_binary(
        str(binary), "claude", label="Claude Code", env_var="CLAUDE_BIN", which=lambda _n: "/otro"
    )

    assert found == str(binary)


def test_resolve_binary_rejects_a_directory_as_binary(tmp_path: Path) -> None:
    with pytest.raises(CliUnavailable):
        resolve_binary(
            str(tmp_path),
            "claude",
            label="Claude Code",
            env_var="CLAUDE_BIN",
            which=lambda _n: "/x",
        )


async def test_working_directory_without_a_resolver_is_a_temporary_directory() -> None:
    async with working_directory(None, uuid4()) as cwd:
        inside = cwd
        assert cwd.is_dir() and list(cwd.iterdir()) == []

    assert not inside.exists()


async def test_working_directory_uses_the_local_folder_and_leaves_it_alone(tmp_path: Path) -> None:
    project = uuid4()
    marker = tmp_path / "datos.txt"
    marker.write_text("mio")

    async with working_directory(FakeProjectPaths({project: str(tmp_path)}), project) as cwd:
        assert cwd == tmp_path

    assert marker.read_text() == "mio"


def test_a_private_directory_is_0700_and_removed() -> None:
    with private_directory() as directory:
        kept = directory
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        (directory / "dentro.txt").write_text("x")

    assert not exists(kept)


def test_a_private_file_is_0600_and_refuses_to_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "secreto.json"

    write_private_file(path, '{"a": 1}')

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.read_text() == '{"a": 1}'
    with pytest.raises(FileExistsError):
        write_private_file(path, "otra cosa")
