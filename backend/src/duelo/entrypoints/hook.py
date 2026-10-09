"""Hook de git: avisa a la API de Duelo de los commits nuevos.

Lo invocan los hooks `post-commit` y `pre-push` que instala la API (`python -m
duelo.entrypoints.hook <evento> --project <slug>`). Solo usa la biblioteca estándar y NUNCA debe
molestar a git: sale siempre con 0, hace el envío en un proceso hijo separado, con un plazo corto,
y se calla ante cualquier error. Los datos del commit los lee con `git` (lista de argumentos, sin
shell) y viajan como JSON: nada de lo que viene del repo llega a un shell.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

# Mismos límites que valida la API (duelo.domain.change): un campo más largo daría 422 y el commit
# no aparecería. Este módulo no importa del paquete a propósito, para arrancar rápido.
MAX_TITLE = 500
MAX_AUTHOR = 255
MAX_REF = 255
MAX_DIFF_CHARS = 1_000_000
MAX_PUSH_COMMITS = 20
SEND_TIMEOUT = 5.0
NO_FORK_TIMEOUT = 2.0
GIT_TIMEOUT = 10.0
ZERO_SHA = "0" * 40
HEADS = "refs/heads/"


def default_env_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "duelo" / "hook.env"


def load_config(env_path: Path | None = None) -> tuple[str, str] | None:
    """`(INGEST_URL, INGEST_TOKEN)`; el entorno manda sobre `hook.env`. `None` si falta algo."""
    values: dict[str, str] = {}
    try:
        for line in (env_path or default_env_path()).read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep:
                values[key.strip()] = value.strip()
    except OSError:
        pass
    url = os.environ.get("INGEST_URL") or values.get("INGEST_URL")
    token = os.environ.get("INGEST_TOKEN") or values.get("INGEST_TOKEN")
    return (url.rstrip("/"), token) if url and token else None


def _git(*args: str) -> str:
    result = subprocess.run(  # noqa: S603 - lista de argumentos, sin shell
        ["git", *args],  # noqa: S607
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=GIT_TIMEOUT,
        check=True,
    )
    return result.stdout


def build_payload(project: str, sha: str, ref: str) -> dict[str, str]:
    """El cuerpo de `POST /ingest/commit` para el commit `sha`."""
    title, author = _git("show", "-s", "--format=%s%x00%an", sha).rstrip("\n").split("\x00", 1)
    diff = _git("show", "--format=", "--patch", sha)
    return {
        "project": project,
        "ref": ref[:MAX_REF],
        "head_sha": sha,
        "title": title[:MAX_TITLE],
        "author": author[:MAX_AUTHOR],
        "diff": diff[:MAX_DIFF_CHARS],
    }


def current_branch() -> str:
    try:
        return _git("symbolic-ref", "--short", "-q", "HEAD").strip() or "HEAD"
    except (subprocess.SubprocessError, OSError):
        return "HEAD"  # cabeza desacoplada


def post(base_url: str, token: str, payload: dict[str, str], timeout: float) -> None:
    request = urllib.request.Request(  # noqa: S310 - la URL es la de la API configurada
        f"{base_url}/ingest/commit",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Ingest-Token": token},
        method="POST",
    )
    urllib.request.urlopen(request, timeout=timeout).close()  # noqa: S310


def pushed_commits(stdin_text: str, remote: str) -> list[tuple[str, str]]:
    """`(sha, rama)` de los commits que se suben, más antiguos primero y a lo sumo
    `MAX_PUSH_COMMITS` por referencia. Se ignoran los borrados y lo que no son ramas."""
    found: list[tuple[str, str]] = []
    for line in stdin_text.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, remote_ref, remote_sha = parts
        if local_sha == ZERO_SHA or not remote_ref.startswith(HEADS):
            continue
        branch = remote_ref[len(HEADS) :]
        if remote_sha == ZERO_SHA:
            revisions = [local_sha, "--not", f"--remotes={remote}"]
        else:
            revisions = [f"{remote_sha}..{local_sha}"]
        try:
            out = _git("rev-list", f"--max-count={MAX_PUSH_COMMITS}", "--reverse", *revisions)
        except (subprocess.SubprocessError, OSError):
            continue
        found.extend((sha, branch) for sha in out.split())
    return found


def _send_all(project: str, commits: Iterable[tuple[str, str]], timeout: float) -> None:
    config = load_config()
    if config is None:
        return
    url, token = config
    for sha, ref in commits:
        try:
            post(url, token, build_payload(project, sha, ref), timeout)
        except Exception:  # noqa: BLE001, S112 - un commit que falla no debe frenar los demás
            continue


def _detach_and_run(  # pragma: no cover - lo ejercitan los tests con procesos reales
    work: Callable[[float], None], *, fallback_timeout: float
) -> None:
    """Ejecuta `work(plazo)` en un hijo separado para que git no espere. Sin `fork` (Windows) lo
    hace en este mismo proceso, con un plazo más corto. El cuerpo corre en procesos hijo que la
    cobertura no sigue; `tests/unit/entrypoints/test_hook.py` lo prueba con git y hooks reales."""
    if not hasattr(os, "fork"):
        work(fallback_timeout)
        return
    if os.fork() != 0:
        return  # el padre vuelve a git de inmediato
    try:
        os.setsid()
        devnull = os.open(os.devnull, os.O_RDWR)
        for fd in (0, 1, 2):
            os.dup2(devnull, fd)
        work(SEND_TIMEOUT)
    finally:
        os._exit(0)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="duelo-hook")
    parser.add_argument("event", choices=["post-commit", "pre-push"])
    parser.add_argument("--project", required=True)
    parser.add_argument("--stdin-file")
    parser.add_argument("remote", nargs="*")
    try:
        args = parser.parse_args(argv)
        if args.event == "post-commit":
            commits = [(_git("rev-parse", "HEAD").strip(), current_branch())]
        else:
            stdin_text = (
                Path(args.stdin_file).read_text(encoding="utf-8") if args.stdin_file else ""
            )
            commits = pushed_commits(stdin_text, args.remote[0] if args.remote else "origin")
        if commits:
            project = args.project
            _detach_and_run(
                lambda timeout: _send_all(project, commits, timeout),
                fallback_timeout=NO_FORK_TIMEOUT,
            )
    except BaseException:  # noqa: BLE001 - un hook jamás debe fallar el commit ni el push
        pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
