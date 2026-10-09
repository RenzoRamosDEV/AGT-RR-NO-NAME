#!/usr/bin/env python3
"""Hook PreToolUse del agente code-guardian: bloquea comandos Bash que escriben.

Es una red de seguridad contra errores (no una defensa contra un adversario: un script
arbitrario siempre puede escribir). Lee el evento de Claude Code por stdin; sale con código 2
(y el motivo por stderr) si el comando modifica archivos, el estado de git o el entorno.
Solo biblioteca estándar.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

# Redirección a un archivo (`> x`, `>> x`); no cuenta `2>&1`, `>&2` ni `> /dev/null`.
_REDIRECT = re.compile(r"(?<![0-9&<])>>?(?!&)\s*(?!/dev/null\b)\S")

_ALWAYS_WRITE = {
    "tee",
    "rm",
    "rmdir",
    "mv",
    "cp",
    "mkdir",
    "touch",
    "chmod",
    "chown",
    "ln",
    "truncate",
    "dd",
    "install",
    "patch",
    "shred",
    "unlink",
}
_GIT_READ_ONLY = {
    "status",
    "diff",
    "log",
    "show",
    "blame",
    "ls-files",
    "ls-remote",
    "rev-parse",
    "describe",
    "merge-base",
    "shortlog",
    "grep",
    "cat-file",
    "config",
    "remote",
    "branch",
    "tag",
    "for-each-ref",
    "name-rev",
    "rev-list",
    "check-ignore",
    "count-objects",
    "fsck",
}
_GIT_READ_ONLY_FLAGGED = {  # subcomandos de lectura que escriben con ciertos argumentos
    "config": {
        "--add",
        "--unset",
        "--unset-all",
        "--replace-all",
        "--edit",
        "-e",
        "--global",
        "--system",
        "--rename-section",
        "--remove-section",
    },
    "remote": {"add", "remove", "rm", "rename", "set-url", "set-head", "prune"},
    "branch": {
        "-d",
        "-D",
        "-m",
        "-M",
        "-c",
        "-C",
        "--delete",
        "--move",
        "--copy",
        "--set-upstream-to",
        "-u",
        "--unset-upstream",
        "--edit-description",
    },
    "tag": {"-d", "-a", "-s", "-f", "--delete", "--annotate", "--sign", "--force"},
}
_JUST_BLOCKED = {"openapi", "gen-client", "migrate", "dev", "down", "worker", "load"}
_SHELL_BLOCKED = {"sudo", "su", "eval"}


def _segments(command: str) -> list[list[str]]:
    parts = re.split(r"\|\||&&|;|\||&|\n", command)
    out: list[list[str]] = []
    for part in parts:
        try:
            tokens = shlex.split(part, comments=False, posix=True)
        except ValueError:
            tokens = part.split()
        while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
            tokens = tokens[1:]  # asignaciones de entorno delante del comando
        if tokens:
            out.append(tokens)
    return out


def _git_reason(args: list[str]) -> str | None:
    # Salta las opciones globales (`-C <dir>`, `-c k=v`, `--no-pager`...) hasta el subcomando.
    index = 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] in {"-C", "-c", "--git-dir", "--work-tree"} else 1
    if index >= len(args):
        return None
    sub, rest = args[index], args[index + 1 :]
    if sub not in _GIT_READ_ONLY:
        return f"git {sub} cambia el estado del repositorio"
    bad = _GIT_READ_ONLY_FLAGGED.get(sub, set())
    if set(rest) & bad:
        return f"git {sub} con {sorted(set(rest) & bad)[0]} escribe"
    positional = [a for a in rest if not a.startswith("-")]
    if (
        sub in {"branch", "tag"}
        and positional
        and not {"--list", "-l", "--contains", "--merged", "--no-merged"} & set(rest)
    ):
        return f"git {sub} <nombre> crea una referencia"
    return None


_WRAPPERS = {"env", "time", "nohup", "nice", "command", "exec", "xargs"}


def _unwrap(tokens: list[str]) -> list[str]:
    """Quita `uv run`, `pnpm exec`, `env`, `time`... para juzgar el programa real."""
    while tokens:
        program = tokens[0].rsplit("/", 1)[-1]
        rest = tokens[1:]
        if program in _WRAPPERS:
            tokens = [t for t in rest if not t.startswith("-")] if program != "xargs" else rest
            continue
        if program == "uv" and rest[:1] == ["run"]:
            tokens = [t for t in rest[1:] if t != "--"]
            while tokens and tokens[0].startswith("-"):
                tokens = (
                    tokens[2:]
                    if tokens[0] in {"--with", "--project", "--directory", "--python", "-p"}
                    else tokens[1:]
                )
            continue
        if program == "pnpm" and rest[:1] in (["exec"], ["dlx"]):
            tokens = rest[1:]
            continue
        break
    return tokens


def _strip_quoted(command: str) -> str:
    return re.sub(r"\'[^']*\'|\"[^\"]*\"", "''", command)


def reason_to_block(command: str) -> str | None:
    if _REDIRECT.search(_strip_quoted(command)):
        return "redirección a un archivo"
    for tokens in _segments(command):
        tokens = _unwrap(tokens)
        if not tokens:
            continue
        program, args = tokens[0].rsplit("/", 1)[-1], tokens[1:]
        if program in _ALWAYS_WRITE:
            return f"{program} modifica archivos"
        if program in _SHELL_BLOCKED:
            return f"{program} no está permitido"
        if program in {"sed", "perl"} and any(
            re.fullmatch(r"-[A-Za-z]*i.*", a) or a == "--in-place" for a in args
        ):
            return f"{program} -i edita archivos"
        if program == "git":
            reason = _git_reason(args)
            if reason:
                return reason
        if program == "uv":
            sub = args[0] if args else ""
            if sub in {"add", "remove", "sync", "init", "tool", "venv", "build", "publish"}:
                return f"uv {sub} cambia el entorno"
            if sub == "lock" and "--check" not in args and "--locked" not in args:
                return "uv lock reescribe el lockfile"
            if sub == "pip" and args[1:2] != ["list"] and args[1:2] != ["show"]:
                return "uv pip modifica el entorno"
        if program in {"pnpm", "npm", "npx", "yarn"} and args:
            if args[0] in {
                "install",
                "i",
                "add",
                "remove",
                "rm",
                "update",
                "up",
                "link",
                "dlx",
                "create",
                "publish",
                "dedupe",
                "prune",
                "import",
            }:
                return f"{program} {args[0]} cambia dependencias"
        if program == "ruff":
            if "--fix" in args or "--unsafe-fixes" in args:
                return "ruff --fix reescribe archivos"
            if args[:1] == ["format"] and "--check" not in args and "--diff" not in args:
                return "ruff format sin --check reescribe archivos"
        if program == "biome" and ("--write" in args or "--fix" in args or "--apply" in args):
            return "biome escribe cambios"
        if program == "just" and args and args[0] in _JUST_BLOCKED:
            return f"just {args[0]} escribe o levanta servicios"
        if (
            program == "alembic"
            and args
            and args[0] in {"upgrade", "downgrade", "revision", "stamp", "merge"}
        ):
            return f"alembic {args[0]} modifica la base de datos o las migraciones"
        if (
            program == "openspec"
            and args
            and args[0] in {"archive", "new", "init", "update", "sync"}
        ):
            return f"openspec {args[0]} modifica archivos"
        if (
            program in {"gh"}
            and len(args) >= 2
            and args[0] in {"pr", "issue", "release"}
            and args[1] in {"create", "merge", "close", "comment", "edit", "review", "reopen"}
        ):
            return f"gh {args[0]} {args[1]} escribe en GitHub"
        if (
            program in {"podman", "docker", "podman-compose", "docker-compose"}
            and args
            and args[0]
            in {
                "rm",
                "rmi",
                "stop",
                "kill",
                "down",
                "prune",
                "system",
                "volume",
                "network",
                "compose",
            }
        ):
            return f"{program} {args[0]} cambia el estado de los contenedores"
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0  # sin evento legible no se bloquea nada
    if event.get("tool_name") != "Bash":
        return 0
    command = str((event.get("tool_input") or {}).get("command", ""))
    reason = reason_to_block(command)
    if reason:
        print(
            f"code-guardian es de solo lectura: bloqueado ({reason}). No ejecutes este comando; "
            "anótalo en 'No verificado' si era una comprobación necesaria.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
