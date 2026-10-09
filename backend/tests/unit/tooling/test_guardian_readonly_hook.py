"""El hook que impide al agente code-guardian escribir: bloquea lo que modifica y deja pasar
las comprobaciones legítimas del repo."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[4] / ".claude" / "hooks" / "guardian-readonly.py"
_spec = importlib.util.spec_from_file_location("guardian_readonly", HOOK)
assert _spec and _spec.loader
guardian = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guardian)

BLOCKED = [
    "echo hola > fichero.txt",
    "cat a >> b",
    "printf x | tee salida.txt",
    "sed -i 's/a/b/' archivo.py",
    "perl -pi -e 's/a/b/' archivo.py",
    "rm -rf backend/mutants",
    "mv a b",
    "cp a b",
    "mkdir /tmp/x",
    "touch x",
    "git commit -m x",
    "git push",
    "git checkout main",
    "git switch -c nueva",
    "git reset --hard",
    "git stash",
    "git clean -fd",
    "git add .",
    "git worktree add /tmp/w HEAD",
    "git -C repo commit -m x",
    "git branch nueva",
    "git branch -D vieja",
    "git tag v1",
    "git config --global user.name x",
    "git remote add o url",
    "uv add requests",
    "uv sync",
    "uv lock",
    "uv pip install x",
    "pnpm install",
    "pnpm add react",
    "npm install",
    "uv run ruff check --fix .",
    "uv run ruff format .",
    "ruff format backend",
    "biome check --write .",
    "just openapi",
    "just migrate",
    "just dev",
    "alembic upgrade head",
    "openspec archive x --yes",
    "gh pr merge 3",
    "gh pr comment 3 -b hola",
    "docker rm x",
    "cd backend && uv run pytest > salida.txt",
    "ls; rm x",
    "ls && git push",
    "sudo ls",
    "FOO=1 rm x",
    "/usr/bin/rm x",
]

ALLOWED = [
    "git status --short",
    "git diff ef2ceec^..ef2ceec",
    "git -C '/var/home/x/new project' show --stat HEAD",
    "git log -1 --format=%s | awk '{print length}'",
    "git blame backend/src/x.py",
    "git branch",
    "git branch --show-current",
    "git tag --list",
    "git remote -v",
    "git config --get user.name",
    "git ls-remote --tags https://github.com/a/b v1",
    "cd backend && uv run ruff check . && uv run ruff format --check .",
    "uv run ruff format --diff .",
    "cd backend && uv run mypy src/ && uv run lint-imports",
    "uv lock --check",
    "uv tree",
    "uv pip list",
    "just test-unit",
    "just test-integration",
    "just mutation",
    "just lint",
    "pnpm exec biome check .",
    "pnpm test",
    "pnpm build",
    "pnpm outdated",
    "pnpm audit",
    "gitleaks detect --no-banner --log-opts='a..b'",
    "gitleaks protect --staged --no-banner -v",
    "gh run list --commit abc123",
    "gh run view 123 --log-failed",
    "gh pr view 3",
    "gh pr diff 3",
    "openspec validate x --strict",
    "openspec list",
    "pytest tests/unit --no-cov -q 2>&1 | tail -5",
    "grep -rn 'x' src | head",
    "uv run pytest tests -q > /dev/null 2>&1",
    "curl -sf http://localhost:8000/health",
    "docker build ./backend",
    "podman ps",
    "ls -la && cat README.md",
    "awk 'BEGIN{print 1>2}'" if False else "echo '1 > 2 es falso'",
]


@pytest.mark.parametrize("command", BLOCKED)
def test_commands_that_write_are_blocked(command: str) -> None:
    assert guardian.reason_to_block(command), command


@pytest.mark.parametrize("command", ALLOWED)
def test_legitimate_checks_are_allowed(command: str) -> None:
    assert guardian.reason_to_block(command) is None, command


def _run(event: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True, text=True
    )


def test_blocking_exits_with_code_2_and_explains_why() -> None:
    result = _run({"tool_name": "Bash", "tool_input": {"command": "rm -rf /tmp/x"}})

    assert result.returncode == 2
    assert "solo lectura" in result.stderr and "rm" in result.stderr


def test_allowed_command_exits_zero_silently() -> None:
    result = _run({"tool_name": "Bash", "tool_input": {"command": "git status"}})

    assert result.returncode == 0 and result.stderr == ""


def test_other_tools_and_garbage_input_are_never_blocked() -> None:
    assert _run({"tool_name": "Read", "tool_input": {"file_path": "x"}}).returncode == 0
    bad = subprocess.run(
        [sys.executable, str(HOOK)], input="no json", capture_output=True, text=True
    )
    assert bad.returncode == 0
