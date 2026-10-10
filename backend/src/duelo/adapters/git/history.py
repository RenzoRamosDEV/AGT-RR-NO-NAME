from __future__ import annotations

import os
import stat
from datetime import UTC, datetime

from duelo.adapters.subprocess_runner import (
    CommandNotFound,
    CommandResult,
    CommandTimeout,
    run_command,
)
from duelo.application.ports import HistoryUnavailable
from duelo.domain.commit_state import Reachability, is_safe_sha_argument

# `git log` sobre 100 000 commits ocupa ~5 MB; más que eso se trata como un fallo, no como un
# conjunto recortado (un recorte por tamaño haría pasar por alcanzable algo que no se vio).
LOG_TIMEOUT_SECONDS = 20.0


class LocalGitHistory:
    """Pregunta al `git` del sistema qué commits son alcanzables en un repositorio local.

    Sin shell y con plazo. Cualquier fallo (carpeta movida, borrada o sustituida por un enlace
    simbólico, git ausente o sin respuesta, repositorio roto) es `HistoryUnavailable`: quien lo use
    no debe marcar nada. Antes de CADA consulta se revalida que la ruta registrada sigue siendo la
    raíz de su repositorio, para no leer (ni marcar a partir de) otro repositorio."""

    async def reachable(self, path: str, *, limit: int) -> Reachability:
        await _ensure_same_repository(path)
        # `--all` incluye todas las referencias y `HEAD`: un commit en cabeza desacoplada o en
        # medio de un rebase sigue contando como alcanzable.
        result = await _git(
            path,
            "log",
            "--all",
            f"--max-count={limit}",
            "--format=%H %ct",
            timeout=LOG_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            raise HistoryUnavailable("git no pudo leer el historial del repositorio")
        if result.truncated:
            raise HistoryUnavailable("El historial es demasiado grande para leerlo entero")
        shas: set[str] = set()
        oldest: int | None = None
        for line in result.stdout.splitlines():
            sha, _, stamp = line.partition(" ")
            if not sha or not stamp.isdigit():
                continue
            shas.add(sha.lower())
            oldest = int(stamp) if oldest is None else min(oldest, int(stamp))
        return Reachability(
            shas=frozenset(shas),
            # Tantos commits como el máximo pedido: puede haber alcanzables fuera de la lista.
            truncated=len(shas) >= limit,
            oldest_at=datetime.fromtimestamp(oldest, UTC) if oldest is not None else None,
        )

    async def contains(self, path: str, sha: str) -> bool:
        # El SHA viene de la ingesta y puede ser cualquier texto: solo un hexadecimal llega a git.
        if not is_safe_sha_argument(sha):
            return False
        rev = sha.lower()
        await _ensure_same_repository(path)
        exists = await _git(path, "cat-file", "-e", f"{rev}^{{commit}}")
        if exists.returncode != 0:
            return False  # el commit ya ni existe en el repositorio
        in_refs = await _git(
            path, "for-each-ref", f"--contains={rev}", "--count=1", "--format=%(refname)"
        )
        if in_refs.returncode != 0:
            raise HistoryUnavailable("git no pudo comprobar las referencias")
        if in_refs.stdout.strip():
            return True
        # Una cabeza desacoplada no es una referencia: se mira aparte.
        ancestor = await _git(path, "merge-base", "--is-ancestor", rev, "HEAD")
        if ancestor.returncode not in (0, 1):
            raise HistoryUnavailable("git no pudo comprobar HEAD")
        return ancestor.returncode == 0


# Un repositorio ajeno (o uno al que se sustituyó la carpeta) no debe poder ejecutar nada ni
# cambiar la configuración con la que se lee: sin configuración de sistema ni de usuario, sin
# `fsmonitor` ni ganchos, y sin variables que redirijan git a otro directorio.
_GIT_ENV = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
_GIT_EXCLUDED_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")
_GIT_HARDENING = ("-c", "core.fsmonitor=false", "-c", f"core.hooksPath={os.devnull}")


async def _ensure_same_repository(path: str) -> None:
    """La ruta registrada debe seguir siendo, tal cual, la raíz de un repositorio: ni un enlace
    simbólico (se rechazan al dar de alta el proyecto) ni una subcarpeta ni otro repositorio."""
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise HistoryUnavailable("La carpeta del proyecto ya no existe") from exc
    if stat.S_ISLNK(info.st_mode):
        raise HistoryUnavailable("La carpeta del proyecto ahora es un enlace simbólico")
    if not stat.S_ISDIR(info.st_mode):
        raise HistoryUnavailable("La ruta del proyecto ya no es una carpeta")
    top = await _git(path, "rev-parse", "--show-toplevel", "--absolute-git-dir")
    if top.returncode != 0:
        raise HistoryUnavailable("La carpeta del proyecto ya no es un repositorio")
    lines = top.stdout.splitlines()
    if len(lines) != 2:
        raise HistoryUnavailable("git no identificó el repositorio de la carpeta del proyecto")
    toplevel, git_dir = lines
    real = os.path.realpath(path)
    if os.path.realpath(toplevel) != real:
        raise HistoryUnavailable("La carpeta del proyecto ya no es la raíz de su repositorio")
    # Un `.git` que es un archivo `gitdir:` (o un enlace) puede apuntar a los objetos de otro
    # repositorio: solo vale el directorio `.git` propio de la carpeta.
    if os.path.realpath(git_dir) != os.path.join(real, ".git"):
        raise HistoryUnavailable("El repositorio de la carpeta del proyecto no está en su .git")


async def _git(path: str, *args: str, timeout: float = 10.0) -> CommandResult:
    try:
        return await run_command(
            ["git", *_GIT_HARDENING, "-C", path, *args],
            timeout=timeout,
            env=_GIT_ENV,
            exclude_env=_GIT_EXCLUDED_ENV,
        )
    except CommandNotFound as exc:
        raise HistoryUnavailable("git no está instalado") from exc
    except CommandTimeout as exc:
        raise HistoryUnavailable("git no respondió a tiempo") from exc
