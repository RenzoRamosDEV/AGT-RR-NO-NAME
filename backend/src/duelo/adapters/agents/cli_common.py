"""Base común de los agentes que revisan con el CLI de la máquina del usuario (`claude`, `codex`).

Cada agente construye sus argumentos y lee su salida; aquí está todo lo demás: localizar el
binario, elegir el directorio de trabajo, el plazo, el límite de concurrencia, el entorno que
hereda el hijo, los errores con mensajes fijos (nunca la salida del CLI) y el log de cada
ejecución. No se usa ninguna clave de API: los CLI se apoyan en la sesión que el usuario ya tiene.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable, Collection, Iterator, Mapping, Sequence
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Protocol
from uuid import UUID

from duelo.adapters.subprocess_runner import (
    CommandNotFound,
    CommandResult,
    CommandTimeout,
    run_command,
)
from duelo.application.ports import ProjectPaths
from duelo.domain.change import Change
from duelo.domain.review import ReviewResult

logger = logging.getLogger("duelo.agents")

# No viajan al CLI: ni los secretos de Duelo ni las claves de API. Con una clave en el entorno el
# CLI la usaría (y facturaría por API) en lugar de la sesión iniciada, que es lo que se quiere.
EXCLUDED_ENV = frozenset(
    {
        "INGEST_TOKEN",
        "OPERATOR_TOKEN",
        "DATABASE_URL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "CODEX_API_KEY",
    }
)
MAX_CLI_OUTPUT_BYTES = 4_000_000
# Los mensajes de error de un CLI van al final de su salida; mirar más atrás solo mete ruido.
ERROR_TAIL_CHARS = 2_000
LOGIN_HINTS = (
    "not logged in",
    "please run /login",
    "run /login",
    "codex login",
    "log in again",
    "sign in",
    "unauthorized",
    "authentication",
    "invalid api key",
)


class CliAgentError(RuntimeError):
    """Un agente de CLI no pudo revisar. El mensaje es fijo y apto para guardarse: nunca incluye la
    salida del CLI, rutas de la máquina ni credenciales."""

    outcome = "error"


class CliUnavailable(CliAgentError):
    outcome = "unavailable"

    def __init__(self, label: str, env_var: str) -> None:
        super().__init__(
            f"El CLI de {label} no está disponible en esta máquina: instálalo o fija {env_var}"
        )


class CliLoginRequired(CliAgentError):
    outcome = "login_required"

    def __init__(self, label: str) -> None:
        super().__init__(
            f"El CLI de {label} no tiene la sesión iniciada: inicia sesión en la terminal"
        )


class CliTimeout(CliAgentError):
    outcome = "timeout"

    def __init__(self, label: str, seconds: float) -> None:
        super().__init__(f"El CLI de {label} no respondió en {seconds:g} s")


class CliFailed(CliAgentError):
    outcome = "failed"

    def __init__(self, label: str, returncode: int) -> None:
        super().__init__(f"El CLI de {label} terminó con error (código {returncode})")


class CliBadOutput(CliAgentError):
    outcome = "bad_output"

    def __init__(self, label: str) -> None:
        super().__init__(f"El CLI de {label} devolvió una respuesta que no cumple el formato")


class CommandRunner(Protocol):
    """Lo que un agente necesita de `run_command`; los tests lo sustituyen por uno falso."""

    async def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: str | None,
        timeout: float,
        env: Mapping[str, str] | None,
        input: str | None,  # noqa: A002
        exclude_env: Collection[str],
        max_output_bytes: int,
    ) -> CommandResult: ...


def looks_like_login_problem(text: str) -> bool:
    tail = text[-ERROR_TAIL_CHARS:].lower()
    return any(hint in tail for hint in LOGIN_HINTS)


def raise_for_failed_command(label: str, result: CommandResult) -> None:
    """Un código de salida distinto de 0: sesión no iniciada si lo parece, error genérico si no."""
    if looks_like_login_problem(result.stderr) or looks_like_login_problem(result.stdout):
        raise CliLoginRequired(label)
    raise CliFailed(label, result.returncode)


def resolve_binary(
    configured: str | None,
    default_name: str,
    *,
    label: str,
    env_var: str,
    which: Callable[[str], str | None] = shutil.which,
) -> str:
    """Ruta del ejecutable: la fijada por configuración (debe existir y poder ejecutarse) o la que
    se encuentre en el `PATH`."""
    if configured:
        if os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        raise CliUnavailable(label, env_var)
    found = which(default_name)
    if found is None:
        raise CliUnavailable(label, env_var)
    return found


@asynccontextmanager
async def working_directory(paths: ProjectPaths | None, project_id: UUID) -> AsyncIterator[Path]:
    """Carpeta del proyecto si es local y existe (el agente puede leerla, solo lectura); si no, un
    directorio temporal vacío (0700) que se borra al salir."""
    local = await paths.path_of(project_id) if paths is not None else None
    if local is not None and Path(local).is_dir():
        yield Path(local)
        return
    scratch = Path(tempfile.mkdtemp(prefix="duelo-agent-"))
    try:
        yield scratch
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


@contextmanager
def private_directory() -> Iterator[Path]:
    """Directorio 0700 para ficheros temporales del CLI (esquema, salida): se borra siempre."""
    directory = Path(tempfile.mkdtemp(prefix="duelo-cli-"))
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def write_private_file(path: Path, content: str) -> None:
    """Crea `path` con permisos 0600 (solo el usuario puede leerlo)."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)


class CliAgent(ABC):
    """Puerto `ReviewAgent` sobre un CLI. Las subclases fijan qué CLI es y cómo se invoca."""

    label: str
    binary_name: str
    binary_env: str
    # ¿El agente puede leer la carpeta del proyecto? Si no, trabaja siempre en un directorio
    # temporal vacío y no se le expone el repositorio.
    uses_project_folder: bool = True

    def __init__(
        self,
        name: str,
        *,
        binary: str | None,
        model: str | None,
        timeout_seconds: float,
        project_paths: ProjectPaths | None,
        limiter: asyncio.Semaphore | None = None,
        runner: CommandRunner = run_command,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.name = name
        self._binary = binary
        self._model = model
        self._timeout = timeout_seconds
        self._project_paths = project_paths
        self._limiter = limiter
        self._runner = runner
        self._which = which

    async def review(self, change: Change) -> ReviewResult:
        started = time.monotonic()
        outcome = "ok"
        try:
            if self._limiter is None:
                return await self._review_in_workdir(change)
            async with self._limiter:  # la espera no cuenta contra el plazo del CLI
                return await self._review_in_workdir(change)
        except CliAgentError as exc:
            outcome = exc.outcome
            raise
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except Exception as exc:
            # Un error nuestro (disco, base de datos…) puede arrastrar rutas: no se guarda su texto.
            outcome = "error"
            raise CliAgentError(f"Error interno al ejecutar el agente {self.name}") from exc
        finally:
            logger.info(
                json.dumps(
                    {
                        "event": "agent_run",
                        "agent": self.name,
                        "duration_ms": int((time.monotonic() - started) * 1000),
                        "outcome": outcome,
                    }
                )
            )

    async def _review_in_workdir(self, change: Change) -> ReviewResult:
        executable = resolve_binary(
            self._binary,
            self.binary_name,
            label=self.label,
            env_var=self.binary_env,
            which=self._which,
        )
        paths = self._project_paths if self.uses_project_folder else None
        async with working_directory(paths, change.project_id) as cwd:
            return await self._run(change, executable, cwd)

    async def _execute(self, argv: Sequence[str], *, input: str, cwd: Path) -> CommandResult:  # noqa: A002
        """Lanza el CLI con el prompt por la entrada estándar y el entorno filtrado."""
        try:
            return await self._runner(
                argv,
                cwd=str(cwd),
                timeout=self._timeout,
                env=None,
                input=input,
                exclude_env=EXCLUDED_ENV,
                max_output_bytes=MAX_CLI_OUTPUT_BYTES,
            )
        except CommandNotFound as exc:
            raise CliUnavailable(self.label, self.binary_env) from exc
        except CommandTimeout as exc:
            raise CliTimeout(self.label, self._timeout) from exc

    @abstractmethod
    async def _run(self, change: Change, executable: str, cwd: Path) -> ReviewResult:
        """Construye los argumentos del CLI, lo ejecuta y devuelve la review ya validada."""
