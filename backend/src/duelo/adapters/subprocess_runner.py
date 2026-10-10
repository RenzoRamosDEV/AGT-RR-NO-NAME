"""Ejecuta programas externos (git, gh, CLI de agentes) sin shell, con plazo y la salida acotada."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
from collections.abc import Collection, Mapping, Sequence
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
    input: str | None = None,  # noqa: A002 - mismo nombre que `subprocess.run`
    exclude_env: Collection[str] = (),
    max_output_bytes: int = MAX_OUTPUT_BYTES,
) -> CommandResult:
    """Lanza `argv` (lista, nunca shell). Lanza `CommandNotFound` o `CommandTimeout`.

    `GIT_TERMINAL_PROMPT=0` evita que git se quede esperando credenciales; `LC_ALL=C` fija el
    idioma de los mensajes de error. `input` se entrega por la entrada estándar (sin él, queda
    cerrada y nada espera datos): sirve para pasar textos grandes o sensibles sin ponerlos en los
    argumentos, que tienen límite de tamaño y se ven en la lista de procesos. `exclude_env` quita
    del entorno heredado esas variables (p. ej. secretos); `env` las puede volver a poner."""
    inherited = {k: v for k, v in os.environ.items() if k not in set(exclude_env)}
    child_env = {**inherited, "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C", **(env or {})}
    try:
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=cwd,
            env=child_env,
            stdin=asyncio.subprocess.DEVNULL if input is None else asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            # Grupo propio: al vencer el plazo se mata también a los hijos del programa.
            start_new_session=True,
        )
    except (FileNotFoundError, PermissionError, NotADirectoryError) as exc:
        raise CommandNotFound(argv[0]) from exc
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(None if input is None else input.encode("utf-8")),
            timeout=timeout,
        )
    except TimeoutError as exc:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        await process.communicate()  # recoge lo que quede y libera las tuberías
        raise CommandTimeout(argv[0]) from exc
    return CommandResult(
        returncode=process.returncode if process.returncode is not None else -1,
        stdout=stdout[:max_output_bytes].decode("utf-8", errors="replace"),
        stderr=stderr[:max_output_bytes].decode("utf-8", errors="replace"),
    )
