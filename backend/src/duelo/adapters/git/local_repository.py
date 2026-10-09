from __future__ import annotations

import os
import stat

from duelo.adapters.subprocess_runner import CommandNotFound, CommandTimeout, run_command
from duelo.application.ports import InvalidRepository, RepoInfo

MAX_PATH = 4096


class LocalGitRepository:
    """Comprueba carpetas con el `git` del sistema."""

    async def inspect(self, path: str) -> RepoInfo:
        _check_path_shape(path)
        try:
            top = await run_command(["git", "-C", path, "rev-parse", "--show-toplevel"])
        except CommandNotFound as exc:
            raise InvalidRepository("git no está instalado") from exc
        except CommandTimeout as exc:
            raise InvalidRepository("git no respondió a tiempo") from exc
        if top.returncode != 0:
            raise InvalidRepository("La ruta no es un repositorio git")
        toplevel = top.stdout.strip()
        if os.path.realpath(toplevel) != os.path.realpath(path):
            raise InvalidRepository("La ruta debe ser la raíz del repositorio, no una subcarpeta")
        return RepoInfo(root=os.path.realpath(path), remote_url=await _origin_url(path))


def _check_path_shape(path: str) -> None:
    if not path or "\x00" in path:
        raise InvalidRepository("La ruta no es válida")
    if len(path) > MAX_PATH:
        raise InvalidRepository("La ruta es demasiado larga")
    if not os.path.isabs(path):
        raise InvalidRepository("La ruta debe ser absoluta")
    if ".." in path.split(os.sep):
        raise InvalidRepository("La ruta no puede contener '..'")
    try:
        mode = os.lstat(path).st_mode
    except OSError as exc:
        raise InvalidRepository("La ruta no existe") from exc
    if stat.S_ISLNK(mode):
        raise InvalidRepository("La ruta no puede ser un enlace simbólico")
    if not stat.S_ISDIR(mode):
        raise InvalidRepository("La ruta no es una carpeta")


async def _origin_url(path: str) -> str | None:
    try:
        result = await run_command(["git", "-C", path, "config", "--get", "remote.origin.url"])
    except (CommandNotFound, CommandTimeout):
        return None
    url = result.stdout.strip()
    return url if result.returncode == 0 and url else None
