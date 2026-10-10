"""Ejecuta programas externos (git, gh, CLI de agentes) sin shell, con plazo y la salida acotada."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass

MAX_OUTPUT_BYTES = 8_000_000
# Tras matar el grupo de procesos se espera como mucho esto a que se cierren sus pipes. Un
# descendiente en otra sesión (`start_new_session=True`) que heredó el stdout sobrevive al
# `killpg` y los mantiene abiertos: sin este plazo, la llamada esperaría a que él terminara.
KILL_GRACE_SECONDS = 2.0


class CommandTimeout(Exception):
    """El programa no terminó en el plazo y se mató."""


class CommandNotFound(Exception):
    """El ejecutable no existe o no se puede ejecutar."""


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    # Verdadero si stdout o stderr superaron `max_output_bytes` y se recortaron: quien interprete
    # la salida no debe darla por completa.
    truncated: bool = False


def _kill_group(process: asyncio.subprocess.Process) -> None:
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)


async def _reap_after_kill(
    process: asyncio.subprocess.Process, communicate: asyncio.Future[tuple[bytes, bytes]]
) -> None:
    """Recoge lo que quede tras matar el grupo, sin esperar más de `KILL_GRACE_SECONDS`.

    Si los pipes siguen abiertos por un descendiente desasociado, abandona la espera y los libera:
    ese descendiente sigue vivo (no hay forma fiable de localizarlo desde aquí), pero la llamada ya
    no queda colgada."""
    done, _ = await asyncio.wait({communicate}, timeout=KILL_GRACE_SECONDS)
    if communicate in done:
        if not communicate.cancelled():
            communicate.exception()  # se consume: nadie va a leer el resultado
        return
    communicate.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await communicate
    # No hay API pública para cerrar los pipes de un `Process`; el transporte los libera.
    transport = getattr(process, "_transport", None)
    if transport is not None:
        with contextlib.suppress(Exception):
            transport.close()
    with contextlib.suppress(Exception):
        await asyncio.wait_for(process.wait(), timeout=KILL_GRACE_SECONDS)


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
    del entorno heredado esas variables (p. ej. secretos); `env` las puede volver a poner. Si la
    salida supera `max_output_bytes` se recorta y el resultado lleva `truncated`."""
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
    communicate = asyncio.ensure_future(
        process.communicate(None if input is None else input.encode("utf-8"))
    )
    try:
        # `shield`: al vencer el plazo la espera se corta pero `communicate` sigue, para poder
        # recoger lo que quede (con su propio plazo) después de matar el grupo.
        stdout, stderr = await asyncio.wait_for(asyncio.shield(communicate), timeout=timeout)
    except TimeoutError as exc:
        _kill_group(process)
        await _reap_after_kill(process, communicate)
        raise CommandTimeout(argv[0]) from exc
    except asyncio.CancelledError:
        # Quien llamó canceló (p. ej. la activity): no se deja el programa corriendo huérfano.
        _kill_group(process)
        communicate.cancel()
        raise
    return CommandResult(
        returncode=process.returncode if process.returncode is not None else -1,
        stdout=stdout[:max_output_bytes].decode("utf-8", errors="replace"),
        stderr=stderr[:max_output_bytes].decode("utf-8", errors="replace"),
        truncated=len(stdout) > max_output_bytes or len(stderr) > max_output_bytes,
    )
