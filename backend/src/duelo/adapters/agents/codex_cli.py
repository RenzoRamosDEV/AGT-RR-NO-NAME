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

# Funciones de Codex que se desactivan (`--disable <nombre>` equivale a
# `-c features.<nombre>=false`; los nombres son los de `codex features list`). Sin
# `shell_tool`/`unified_exec` el modelo no puede ejecutar comandos ni leer ficheros: `-s read-only`
# solo impide ESCRIBIR, y se comprobó que con él un prompt «ejecuta cat /etc/hostname» devolvía el
# contenido. El resto cierra otras vías de salir del directorio de trabajo (visor de imágenes,
# navegador, aplicaciones, plugins) y `hooks` impide que corran los hooks del usuario dentro de la
# review.
DISABLED_FEATURES = (
    "shell_tool",
    "unified_exec",
    "hooks",
    "view_image",
    "apps",
    "plugins",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "computer_use",
    "in_app_browser",
    "image_generation",
)


class CodexCliAgent(CliAgent):
    label = "Codex"
    binary_name = "codex"
    binary_env = "CODEX_BIN"
    # Sin herramienta de shell Codex no puede leer ficheros: revisa solo el diff y no se le da el
    # repositorio del proyecto.
    uses_project_folder = False

    def build_args(self, executable: str, *, schema: Path, output: Path, cwd: Path) -> list[str]:
        """Argumentos del CLI. El prompt NO va aquí: el `-` final lo lee de la entrada estándar.

        - `-s read-only`: el sandbox de Codex no deja escribir (y mantiene la red cerrada).
        - `--ignore-user-config` / `--ignore-rules`: no carga el `config.toml` ni las reglas de
          ejecución del usuario (la sesión iniciada sigue en `CODEX_HOME`).
        - `--disable <función>`: sin herramienta de shell ni de salida del directorio (ver
          `DISABLED_FEATURES`): el modelo no puede ejecutar comandos ni leer fuera del diff.
        - `--ephemeral`: no guarda la sesión. `--skip-git-repo-check`: el directorio es temporal.
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
            "--ignore-user-config",
            "--ignore-rules",
            *[arg for feature in DISABLED_FEATURES for arg in ("--disable", feature)],
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
                # Se mide ANTES de leer: un mensaje que supera el límite no se parsea recortado.
                if output.stat().st_size > MAX_LAST_MESSAGE_BYTES:
                    raise CliBadOutput(self.label)
                text = output.read_bytes().decode("utf-8")
                return parse_review_payload(json.loads(text))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, InvalidReviewPayload) as exc:
                raise CliBadOutput(self.label) from exc
