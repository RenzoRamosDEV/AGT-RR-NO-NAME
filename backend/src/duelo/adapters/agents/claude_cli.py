"""Agente de revisión sobre Claude Code (`claude -p`), con la sesión que el usuario ya tiene."""

from __future__ import annotations

import asyncio
import json
import shutil
from collections.abc import Callable
from pathlib import Path

from duelo.adapters.agents.cli_common import (
    CliAgent,
    CliBadOutput,
    CliFailed,
    CliLoginRequired,
    CommandRunner,
    looks_like_login_problem,
    raise_for_failed_command,
)
from duelo.adapters.agents.review_payload import (
    REVIEW_SCHEMA,
    InvalidReviewPayload,
    build_prompt,
    parse_review_payload,
)
from duelo.adapters.subprocess_runner import CommandResult, run_command
from duelo.application.ports import ProjectPaths
from duelo.domain.change import Change
from duelo.domain.review import ReviewResult

# Solo lectura: nada de Bash, Edit, Write ni WebFetch.
READ_ONLY_TOOLS = "Read,Grep,Glob"
DEFAULT_MAX_BUDGET_USD = 2.0


class ClaudeCliAgent(CliAgent):
    label = "Claude Code"
    binary_name = "claude"
    binary_env = "CLAUDE_BIN"

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
        max_budget_usd: float = DEFAULT_MAX_BUDGET_USD,
    ) -> None:
        super().__init__(
            name,
            binary=binary,
            model=model,
            timeout_seconds=timeout_seconds,
            project_paths=project_paths,
            limiter=limiter,
            runner=runner,
            which=which,
        )
        self._max_budget_usd = max_budget_usd

    def build_args(self, executable: str) -> list[str]:
        """Argumentos del CLI. El prompt NO va aquí: se entrega por la entrada estándar.

        - `--tools Read,Grep,Glob` + `--permission-mode dontAsk` + `--permission-prompts none`:
          solo lectura y nunca se queda esperando una confirmación.
        - `--strict-mcp-config`, `--disable-slash-commands`, `--setting-sources ""`: no carga los
          MCP, las skills ni los hooks del usuario (la sesión OAuth sí se sigue usando; `--bare`
          no, por eso no se usa).
        - `--no-session-persistence`: no deja la conversación en disco.
        - `--max-budget-usd`: tope contra un bucle de herramientas desbocado.
        """
        args = [
            executable,
            "-p",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(REVIEW_SCHEMA),
            "--no-session-persistence",
            "--tools",
            READ_ONLY_TOOLS,
            "--permission-mode",
            "dontAsk",
            "--permission-prompts",
            "none",
            "--strict-mcp-config",
            "--disable-slash-commands",
            "--setting-sources",
            "",
            "--max-budget-usd",
            f"{self._max_budget_usd:g}",
        ]
        if self._model:
            args += ["--model", self._model]
        return args

    async def _run(self, change: Change, executable: str, cwd: Path) -> ReviewResult:
        result = await self._execute(
            self.build_args(executable), input=build_prompt(change), cwd=cwd
        )
        return self._parse(result)

    def _parse(self, result: CommandResult) -> ReviewResult:
        """Lee el objeto JSON de `--output-format json`: `structured_output` ya validado contra el
        esquema, o `result` (el mismo JSON como texto) si no viene."""
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            if result.returncode != 0:
                raise_for_failed_command(self.label, result)
            raise CliBadOutput(self.label) from exc
        if not isinstance(data, dict):
            raise CliBadOutput(self.label)
        if data.get("is_error") or result.returncode != 0:
            text = data.get("result")
            if looks_like_login_problem(text if isinstance(text, str) else "") or (
                looks_like_login_problem(result.stderr)
            ):
                raise CliLoginRequired(self.label)
            raise CliFailed(self.label, result.returncode or 1)
        payload = data.get("structured_output")
        if payload is None:
            raw = data.get("result")
            try:
                payload = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError as exc:
                raise CliBadOutput(self.label) from exc
        try:
            return parse_review_payload(payload)
        except InvalidReviewPayload as exc:
            raise CliBadOutput(self.label) from exc
