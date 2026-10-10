# Design

## Clasificación de las funciones de Codex

Se partió de `codex features list` completo en esta máquina (Codex 0.162.1): 58 funciones habilitadas,
de las que algunas son `removed` (no hacen nada y se ignoran). El criterio:

- **Desactivar** lo que ejecuta código o shell, lee el disco o el workspace, lanza subagentes o amplía
  las herramientas del modelo, o usa red, plugins o MCP.
- **Permitir** solo lo claramente benigno y necesario o neutro: interfaz, telemetría, transporte y
  compatibilidad. Cada una con el motivo, en el código (`REVIEWED_ALLOWED_FEATURES`).
- **Ante la duda, desactivar:** apagar una función benigna no cuesta nada (se verifica con una review
  real), y dejar una dudosa abierta sí.

`DISABLED_FEATURES` pasa de 12 a 30 funciones. Se añaden, entre otras, `unified_exec_tty`,
`shell_snapshot` (captura el entorno de shell del usuario), `multi_agent` (subagentes),
`skill_mcp_dependency_install`, `skill_search`, `workspace_dependencies`, `worktrees`,
`code_mode_host`, `plugin_sharing`, `remote_plugin`, `tool_suggest`, `tool_call_mcp_elicitation`,
`mentions_v2`, `goals`, `daemon_auto_start`, `realtime_conversation`, `in_app_local_automation` y
`browser_annotation_api`. Quedan permitidas, por ejemplo, `guardian_approval` (un mecanismo de
seguridad de Codex, que conviene mantener), `sleep_tool`, `fast_mode`, `system_proxy_fallback` o las de
interfaz `in_app_*`.

## El guardián contra funciones nuevas

La lógica es una función pura en `codex_cli.py`, `unreviewed_features(listing)`: analiza la salida de
`codex features list` (`nombre  etapa  habilitada`), ignora las `removed` y las deshabilitadas, y
devuelve las habilitadas que no están en `DISABLED_FEATURES` ni en `REVIEWED_ALLOWED_FEATURES`.

- Test unitario con una salida falsa: cubre todos los casos (clasificada, sin clasificar, `removed`,
  deshabilitada, líneas basura, listas disjuntas y completas).
- Test contra el `codex` real (`tests/integration/agents/test_codex_features.py`): se salta si falta
  el binario. **No consume suscripción** (`codex features list` no llama al modelo), así que corre en
  la suite normal de quien lo tenga instalado, y falla nombrando la función si una versión nueva trae
  una sin clasificar. En la CI no hay `codex`, así que se salta.

## Cancelación de `run_command`

La rama `except asyncio.CancelledError` hacía `killpg` y `communicate.cancel()` y relanzaba. Ahora hace
`killpg` y espera `_reap_after_kill(...)` (el mismo camino que el plazo vencido: espera acotada,
cancela, cierra el transporte y espera al proceso) envuelto en `asyncio.shield`, de modo que una
segunda cancelación no corta la recolección a medias, y relanza `CancelledError` al final. El tiempo
máximo añadido a una cancelación es `KILL_GRACE_SECONDS` por cada espera (≤ 4 s con pipes retenidos).

## Riesgo residual (no se promete más de lo que se hace)

- **Codex:** lista de denegación + sandbox `read-only` + directorio de trabajo temporal vacío + entorno
  sin secretos ni claves de API + test que obliga a revisar las funciones nuevas. Una herramienta nueva
  que un test no pudiera detectar (por ejemplo, una que no aparezca en `codex features list`) no
  estaría desactivada.
- **Descendiente desasociado:** si un CLI deja un proceso en otra sesión que retiene los pipes, la
  llamada ya no se cuelga, pero ese proceso **no se localiza ni se mata** y puede seguir vivo. Se acepta.
