from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from duelo.adapters.subprocess_runner import CommandNotFound, CommandTimeout, run_command


async def test_returns_code_and_decoded_output() -> None:
    result = await run_command(
        [
            sys.executable,
            "-c",
            "import sys; print('hola ñ'); print('mal', file=sys.stderr); sys.exit(3)",
        ]
    )

    assert (result.returncode, result.stdout, result.stderr) == (3, "hola ñ\n", "mal\n")


async def test_arguments_are_never_interpreted_by_a_shell(tmp_path: Path) -> None:
    marker = tmp_path / "pwned"

    result = await run_command(["echo", f"x; touch {marker}"])

    assert result.stdout == f"x; touch {marker}\n"
    assert not marker.exists()


async def test_runs_in_the_given_directory(tmp_path: Path) -> None:
    result = await run_command(["pwd"], cwd=str(tmp_path))

    assert Path(result.stdout.strip()).resolve() == tmp_path.resolve()


async def test_extra_environment_is_passed_on_and_git_never_prompts() -> None:
    result = await run_command(
        [
            sys.executable,
            "-c",
            "import os; print(os.environ['X'], os.environ['GIT_TERMINAL_PROMPT'])",
        ],
        env={"X": "valor"},
    )

    assert result.stdout == "valor 0\n"


async def test_a_command_that_exceeds_the_timeout_is_killed() -> None:
    started = time.monotonic()

    with pytest.raises(CommandTimeout):
        await run_command([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.3)

    assert time.monotonic() - started < 5


async def test_a_missing_executable_is_reported_as_such() -> None:
    with pytest.raises(CommandNotFound):
        await run_command(["no-existe-este-programa-duelo"])


async def test_stdin_is_closed_so_nothing_waits_for_input() -> None:
    result = await run_command([sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))"])

    assert result.stdout == "''\n"


@pytest.mark.regression
async def test_a_timeout_also_kills_the_children_of_the_command() -> None:
    """Origen: un `gh` colgado dejaba a su hijo sujetando las tuberías y la llamada tardaba
    lo que el hijo, no lo que decía el plazo."""
    started = time.monotonic()

    with pytest.raises(CommandTimeout):
        await run_command(["sh", "-c", "sleep 30 & wait"], timeout=0.3)

    assert time.monotonic() - started < 5
