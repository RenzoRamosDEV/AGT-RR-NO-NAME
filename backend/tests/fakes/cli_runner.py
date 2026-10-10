from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from duelo.adapters.subprocess_runner import CommandResult
from duelo.domain.change import Change, ChangeKind


@dataclass(frozen=True, slots=True)
class RunnerCall:
    argv: list[str]
    cwd: str | None
    timeout: float
    env: Mapping[str, str] | None
    input: str | None
    exclude_env: Collection[str]
    max_output_bytes: int


class FakeRunner:
    """Sustituye a `run_command`: no lanza nada, anota la llamada y devuelve lo que se le diga."""

    def __init__(
        self,
        *,
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
        raises: BaseException | None = None,
        on_call: Callable[[RunnerCall], None] | None = None,
    ) -> None:
        self._result = CommandResult(returncode=returncode, stdout=stdout, stderr=stderr)
        self._raises = raises
        self._on_call = on_call
        self.calls: list[RunnerCall] = []

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
    ) -> CommandResult:
        call = RunnerCall(list(argv), cwd, timeout, env, input, exclude_env, max_output_bytes)
        self.calls.append(call)
        if self._on_call is not None:
            self._on_call(call)
        if self._raises is not None:
            raise self._raises
        return self._result


class FakeProjectPaths:
    """Implementa `ProjectPaths` con un diccionario `project_id -> ruta`."""

    def __init__(self, paths: dict[UUID, str] | None = None) -> None:
        self._paths = paths or {}

    async def path_of(self, project_id: UUID) -> str | None:
        return self._paths.get(project_id)


def make_change(
    *,
    diff: str = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-x\n+y\n",
    title: str = "fix: algo",
    project_id: UUID | None = None,
) -> Change:
    return Change.new(
        project_id=project_id or uuid4(),
        kind=ChangeKind.COMMIT,
        ref="main",
        head_sha="b" * 40,
        title=title,
        author="ana",
        url="https://example.com",
        diff=diff,
        diff_truncated=False,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def option_value(argv: Sequence[str], flag: str) -> str:
    """El valor que sigue a `flag` en `argv`."""
    return argv[list(argv).index(flag) + 1]


def exists(path: str | Path | None) -> bool:
    return path is not None and Path(path).exists()
