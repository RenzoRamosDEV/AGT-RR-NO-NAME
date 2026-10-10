from __future__ import annotations

import asyncio
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


async def test_input_reaches_the_child_through_stdin_and_never_through_the_arguments() -> None:
    secret = "diff con ñ y un secreto " * 20_000  # ~480 KB: más que un argumento permitido

    result = await run_command(
        [sys.executable, "-c", "import sys; print(len(sys.stdin.read()))"], input=secret
    )

    assert result.stdout == f"{len(secret)}\n"


async def test_a_child_that_exits_without_reading_its_input_does_not_hang() -> None:
    result = await run_command([sys.executable, "-c", "pass"], input="x" * 5_000_000, timeout=5)

    assert result.returncode == 0


async def test_excluded_variables_are_not_inherited_but_the_rest_are(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRETO_DE_PRUEBA", "no-debe-llegar")
    monkeypatch.setenv("VISIBLE_DE_PRUEBA", "si-llega")
    code = (
        "import os; print(os.environ.get('SECRETO_DE_PRUEBA'), os.environ.get('VISIBLE_DE_PRUEBA'))"
    )

    result = await run_command([sys.executable, "-c", code], exclude_env={"SECRETO_DE_PRUEBA"})

    assert result.stdout == "None si-llega\n"


async def test_an_explicit_env_can_set_back_an_excluded_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("X_EXCLUIDA", "heredada")

    result = await run_command(
        [sys.executable, "-c", "import os; print(os.environ['X_EXCLUIDA'])"],
        exclude_env={"X_EXCLUIDA"},
        env={"X_EXCLUIDA": "explicita"},
    )

    assert result.stdout == "explicita\n"


async def test_a_running_command_does_not_block_the_event_loop() -> None:
    """Los latidos de la activity corren en el mismo bucle que espera al CLI: si el subproceso lo
    bloqueara, una review lenta vencería el `heartbeat_timeout`."""
    ticks = 0

    async def heartbeat() -> None:
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0.02)

    beat = asyncio.create_task(heartbeat())
    try:
        await run_command([sys.executable, "-c", "import time; time.sleep(0.5)"], timeout=5)
    finally:
        beat.cancel()

    assert ticks >= 10  # ~25 latidos de 20 ms en medio segundo; un bucle bloqueado daría 1


async def test_the_output_limit_can_be_lowered_per_call() -> None:
    result = await run_command([sys.executable, "-c", "print('a' * 1000)"], max_output_bytes=10)

    assert result.stdout == "a" * 10
