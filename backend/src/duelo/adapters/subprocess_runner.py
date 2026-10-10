"""Ejecuta programas externos (git, gh) sin shell, con plazo y con la salida acotada."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

MAX_OUTPUT_BYTES = 8_000_000


class CommandTimeout(Exception):
    """El programa no terminó en el plazo y se mató."""


class CommandNotFound(Exception):
    """El ejecutable no existe o no se puede ejecutar."""


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


async def run_command(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    timeout: float = 10.0,
    env: Mapping[str, str] | None = None,
) -> CommandResult:
    """Lanza `argv` (lista, nunca shell). Lanza `CommandNotFound` o `CommandTimeout`.

    `GIT_TERMINAL_PROMPT=0` evita que git se quede esperando credenciales; `LC_ALL=C` fija el
    idioma de los mensajes de error."""
    child_env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C", **(env or {})}
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            env=child_env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # Grupo propio: al vencer el plazo se mata también a los hijos del programa.
            start_new_session=True,
        )
    except (FileNotFoundError, PermissionError, NotADirectoryError) as exc:
        raise CommandNotFound(argv[0]) from exc
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError as exc:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        await process.communicate()  # recoge lo que quede y libera las tuberías
        raise CommandTimeout(argv[0]) from exc
    return CommandResult(
        returncode=process.returncode if process.returncode is not None else -1,
        stdout=stdout[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"),
        stderr=stderr[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"),
    )
