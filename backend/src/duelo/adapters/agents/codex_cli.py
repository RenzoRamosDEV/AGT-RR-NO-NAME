"""Agente de revisión sobre Codex (`codex exec`), con la sesión que el usuario ya tiene."""

from __future__ import annotations

import json
from pathlib import Path

from duelo.adapters.agents.cli_common import (
    CliAgent,
    CliBadOutput,
    private_directory,
    raise_for_failed_command,
    write_private_file,
)
from duelo.adapters.agents.review_payload import (
    REVIEW_SCHEMA,
    InvalidReviewPayload,
    build_prompt,
    parse_review_payload,
)
from duelo.domain.change import Change
from duelo.domain.review import ReviewResult

MAX_LAST_MESSAGE_BYTES = 1_000_000


class CodexCliAgent(CliAgent):
    label = "Codex"
    binary_name = "codex"
    binary_env = "CODEX_BIN"

    def build_args(self, executable: str, *, schema: Path, output: Path, cwd: Path) -> list[str]:
        """Argumentos del CLI. El prompt NO va aquí: el `-` final lo lee de la entrada estándar.

        - `-s read-only`: el sandbox de Codex no deja escribir ni ejecutar nada que modifique.
        - `--ephemeral`: no guarda la sesión. `--skip-git-repo-check`: el directorio puede no ser
          un repositorio (uno temporal vacío).
        - `--output-schema` / `-o`: el último mensaje se valida contra el esquema y se escribe en
          un fichero, que es lo que se lee (stdout lleva además la transcripción y los hooks).
        """
        args = [
            executable,
            "exec",
            "-s",
            "read-only",
            "--ephemeral",
            "--skip-git-repo-check",
            "--output-schema",
            str(schema),
            "-o",
            str(output),
            "-C",
            str(cwd),
        ]
        if self._model:
            args += ["-m", self._model]
        return [*args, "-"]

    async def _run(self, change: Change, executable: str, cwd: Path) -> ReviewResult:
        with private_directory() as scratch:
            schema, output = scratch / "schema.json", scratch / "last-message.json"
            write_private_file(schema, json.dumps(REVIEW_SCHEMA))
            args = self.build_args(executable, schema=schema, output=output, cwd=cwd)
            result = await self._execute(args, input=build_prompt(change), cwd=cwd)
            if result.returncode != 0:
                raise_for_failed_command(self.label, result)
            try:
                text = output.read_bytes()[:MAX_LAST_MESSAGE_BYTES].decode("utf-8")
                return parse_review_payload(json.loads(text))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, InvalidReviewPayload) as exc:
                raise CliBadOutput(self.label) from exc
