"""Instala y quita los hooks de git de Duelo sin pisar los del usuario."""

from __future__ import annotations

import os
import re
import stat
import tempfile
from pathlib import Path

from duelo.adapters.subprocess_runner import CommandNotFound, CommandTimeout, run_command
from duelo.application.ports import HookInstallError

BEGIN = "# >>> duelo >>>"
END = "# <<< duelo <<<"
DEFAULT_SHEBANG = "#!/bin/sh"
HOOK_NAMES = ("post-commit", "pre-push")
_SHELL_SHEBANG = re.compile(
    r"^#!\s*(?:/usr/bin/env\s+(?:-S\s+)?)?(?:\S*/)?(?:sh|bash|dash|zsh|ksh)\b"
)


def _quote(value: str) -> str:
    """Comillas simples de shell: nada de lo que va dentro se interpreta."""
    return "'" + value.replace("'", "'\\''") + "'"


def render_block(hook: str, *, python: str, slug: str, env_path: str) -> str:
    """El bloque de Duelo para `hook`. Solo lleva datos que fija el instalador (ruta del intérprete,
    slug y ruta del fichero de credenciales, entre comillas simples); lo que viene de git lo lee el
    módulo del hook, no el shell."""
    command = (
        f"{_quote(python)} -m duelo.entrypoints.hook {hook} --project {_quote(slug)}"
        f" --env-file {_quote(env_path)}"
    )
    if hook == "pre-push":
        # Git entrega las referencias por stdin. Se vuelcan a un fichero para dárselas al módulo
        # y se restauran en stdin para los hooks del usuario que vengan después.
        lines = [
            '__duelo_in=$(mktemp 2>/dev/null) || __duelo_in=""',
            'if [ -n "$__duelo_in" ]; then',
            '  cat > "$__duelo_in"',
            f'  {command} --stdin-file "$__duelo_in" "$@" >/dev/null 2>&1 || true',
            '  exec < "$__duelo_in"',
            '  rm -f "$__duelo_in"',
            "fi",
            "unset __duelo_in",
        ]
    else:
        lines = [f'{command} "$@" >/dev/null 2>&1 || true']
    return "\n".join([BEGIN, *lines, END])


def _strip_block(text: str) -> str:
    out: list[str] = []
    skipping = False
    for line in text.split("\n"):
        if line == BEGIN:
            skipping = True
            continue
        if skipping:
            if line == END:
                skipping = False
            continue
        out.append(line)
    return "\n".join(out)


def insert_block(existing: str | None, block: str) -> str:
    """Hook resultante: `existing` sin bloques anteriores y con `block` justo tras el shebang."""
    if existing is None:
        return f"{DEFAULT_SHEBANG}\n{block}\n"
    lines = _strip_block(existing).split("\n")
    at = 1 if lines and lines[0].startswith("#!") else 0
    return "\n".join([*lines[:at], block, *lines[at:]])


def remove_block(existing: str) -> str | None:
    """`existing` sin el bloque de Duelo, o `None` si el hook se queda vacío (solo el shebang)."""
    remaining = _strip_block(existing)
    return None if remaining.strip() in {"", DEFAULT_SHEBANG} else remaining


def _is_shell_script(text: str) -> bool:
    first = text.split("\n", 1)[0]
    return not first.startswith("#!") or _SHELL_SHEBANG.match(first) is not None


class FileHookInstaller:
    def __init__(self, *, python: str, ingest_url: str, ingest_token: str, env_path: Path) -> None:
        self._python = python
        self._ingest_url = ingest_url
        self._ingest_token = ingest_token
        self._env_path = env_path

    async def install(self, root: str, *, slug: str) -> None:
        if "\n" in self._ingest_token or "\r" in self._ingest_token:
            raise HookInstallError("El token de ingesta no puede contener saltos de línea")
        hooks_dir = await _hooks_dir(root)
        originals: dict[str, str | None] = {}
        planned: dict[str, str] = {}
        for name in HOOK_NAMES:
            path = hooks_dir / name
            existing = _read_hook(path)
            originals[name] = existing
            planned[name] = insert_block(
                existing,
                render_block(
                    name, python=self._python, slug=slug, env_path=os.path.abspath(self._env_path)
                ),
            )
        # Todo comprobado: a partir de aquí solo escritura (con vuelta atrás si falla).
        self._write_env()
        written: list[str] = []
        try:
            hooks_dir.mkdir(parents=True, exist_ok=True)
            for name, content in planned.items():
                _write_hook(hooks_dir / name, content)
                written.append(name)
        except OSError as exc:
            for name in written:
                _restore(hooks_dir / name, originals[name])
            raise HookInstallError("No se pudieron escribir los hooks") from exc

    async def uninstall(self, root: str) -> None:
        if not os.path.isdir(root):
            return
        try:
            hooks_dir = await _hooks_dir(root)
        except HookInstallError:
            return  # sin hooks reconocibles no hay nada que quitar
        for name in HOOK_NAMES:
            path = hooks_dir / name
            if path.is_symlink() or not path.is_file():
                continue
            try:
                existing = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if BEGIN not in existing:
                continue
            remaining = remove_block(existing)
            if remaining is None:
                path.unlink()
            else:
                _write_hook(path, remaining)

    def _write_env(self) -> None:
        directory = self._env_path.parent
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        content = f"INGEST_URL={self._ingest_url}\nINGEST_TOKEN={self._ingest_token}\n"
        fd = os.open(self._env_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(self._env_path, 0o600)  # por si el fichero ya existía con otro modo


async def _hooks_dir(root: str) -> Path:
    """Directorio de hooks efectivo (worktrees y `core.hooksPath` incluidos), que debe estar dentro
    del repo o de su directorio común: uno compartido entre repos ejecutaría el bloque en todos."""
    try:
        result = await run_command(
            [
                "git",
                "-C",
                root,
                "rev-parse",
                "--path-format=absolute",
                "--git-path",
                "hooks",
                "--git-common-dir",
            ]
        )
    except (CommandNotFound, CommandTimeout) as exc:
        raise HookInstallError("git no está disponible") from exc
    lines = result.stdout.splitlines()
    if result.returncode != 0 or len(lines) != 2:
        raise HookInstallError("No se pudo localizar el directorio de hooks del repo")
    hooks, common = Path(os.path.realpath(lines[0])), Path(os.path.realpath(lines[1]))
    repo = Path(os.path.realpath(root))
    if not any(hooks.is_relative_to(base) for base in (repo, common)):
        raise HookInstallError(
            "core.hooksPath apunta fuera del repo: Duelo no instala hooks en carpetas compartidas"
        )
    return hooks


def _read_hook(path: Path) -> str | None:
    if path.is_symlink():
        raise HookInstallError(f"El hook {path.name} es un enlace simbólico")
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise HookInstallError(f"No se puede leer el hook {path.name}") from exc
    if not _is_shell_script(text):
        raise HookInstallError(f"El hook {path.name} existente no es un script de shell")
    return text


def _write_hook(path: Path, content: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o755
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(tmp, mode | 0o111)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _restore(path: Path, original: str | None) -> None:
    try:
        if original is None:
            path.unlink(missing_ok=True)
        else:
            _write_hook(path, original)
    except OSError:
        pass  # mejor esfuerzo: ya estamos propagando el error original
