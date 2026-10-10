"""Agente de revisión sobre Codex (`codex exec`), con la sesión que el usuario ya tiene."""

from __future__ import annotations

import json
import re
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

# Todas las funciones HABILITADAS de `codex features list` (salvo las `removed`, que no hacen nada)
# están clasificadas en una de estas dos listas; un test falla si el CLI muestra una habilitada que
# no esté en ninguna (`unreviewed_features`), de modo que una versión nueva de Codex no incorpore
# herramientas sin que alguien las revise. Es una lista de DENEGACIÓN: la defensa no descansa solo
# en ella (sandbox `read-only`, directorio de trabajo temporal vacío, entorno sin secretos).
#
# Se desactivan (`--disable <nombre>` equivale a `-c features.<nombre>=false`): lo que ejecuta
# código o comandos, lee el disco o el workspace, lanza subagentes o amplía las herramientas del
# modelo, o usa red, plugins o MCP. `-s read-only` solo impide ESCRIBIR: con él un prompt «ejecuta
# cat /etc/hostname» devolvía el contenido, y sin `shell_tool`/`unified_exec` ya no. `hooks` además
# impide que corran los hooks del usuario dentro de la review. Ante la duda se desactiva: apagar una
# función benigna no cuesta nada y dejar una dudosa abierta sí.
DISABLED_FEATURES = (
    "apps",
    "browser_annotation_api",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "code_mode_host",
    "computer_use",
    "daemon_auto_start",
    "goals",
    "hooks",
    "image_generation",
    "in_app_browser",
    "in_app_local_automation",
    "mentions_v2",
    "multi_agent",
    "plugin_sharing",
    "plugins",
    "realtime_conversation",
    "remote_plugin",
    "shell_snapshot",
    "shell_tool",
    "skill_mcp_dependency_install",
    "skill_search",
    "tool_call_mcp_elicitation",
    "tool_suggest",
    "unified_exec",
    "unified_exec_tty",
    "view_image",
    "workspace_dependencies",
    "worktrees",
)

# Revisadas y permitidas: interfaz, telemetría, transporte y compatibilidad, sin acceso al disco, a
# comandos, a red de herramientas ni a subagentes. El motivo de cada una queda aquí.
REVIEWED_ALLOWED_FEATURES: dict[str, str] = {
    "api_key_model_discovery": "descubrimiento de modelos con la credencial; no es una herramienta",
    "auth_elicitation": "petición de autenticación del propio CLI",
    "compaction_image_budget": "presupuesto de imágenes al compactar el contexto",
    "content_item_kinds": "formato de los elementos del protocolo",
    "enable_request_compression": "compresión de las peticiones a la API",
    "fast_mode": "modo de servicio rápido del modelo",
    "guardian_approval": "revisor de seguridad de aprobaciones de Codex: conviene mantenerlo",
    "guardian_reuse_parent_compaction": "optimización del revisor de seguridad",
    "in_app_chat": "interfaz de la app de escritorio; no aplica a `codex exec`",
    "in_app_dictation": "interfaz de la app de escritorio; no aplica a `codex exec`",
    "in_app_updates": "interfaz de la app de escritorio; no aplica a `codex exec`",
    "in_app_voice": "interfaz de la app de escritorio; no aplica a `codex exec`",
    "instant_interrupt": "interrupción inmediata de un turno (experiencia de uso)",
    "sleep_tool": "espera sin efectos sobre el disco, la red ni los procesos",
    "system_proxy_fallback": "respaldo de proxy del sistema para la conexión con la API",
    "ultrafast_mode": "modo de servicio de menor latencia",
    "unbounded_connection_retries": "reintentos de conexión con la API (los acota el plazo)",
    "write_stdin_approval": "aprobación de escribir en stdin de una ejecución (inerte sin shell)",
}

_FEATURE_LINE = re.compile(r"^(?P<name>\S+)\s+(?P<stage>.+?)\s+(?P<enabled>true|false)\s*$")


def unreviewed_features(listing: str) -> list[str]:
    """Funciones habilitadas en `listing` (la salida de `codex features list`: `nombre etapa
    habilitada`) que no están ni desactivadas ni revisadas y permitidas. Ignora las `removed` y las
    deshabilitadas. Una lista no vacía significa que una versión de Codex trae algo sin revisar."""
    classified = set(DISABLED_FEATURES) | set(REVIEWED_ALLOWED_FEATURES)
    found: set[str] = set()
    for line in listing.splitlines():
        match = _FEATURE_LINE.match(line.strip())
        if match is None or match["enabled"] != "true" or match["stage"] == "removed":
            continue
        if match["name"] not in classified:
            found.add(match["name"])
    return sorted(found)


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
