# Proposal

## Why

La segunda revisión de Codex sobre `harden-cli-agents` señaló dos problemas. Ambos se han comprobado:

1. **La lista de funciones de Codex desactivadas es de denegación y se queda corta.** Con
   `codex features list` completo en esta máquina hay 58 funciones habilitadas (varias ya `removed`,
   sin efecto) y la lista solo desactivaba 12. Seguían activas, entre otras, `unified_exec_tty`,
   `shell_snapshot`, `multi_agent` (subagentes), `skill_mcp_dependency_install`, `skill_search`,
   `workspace_dependencies`, `worktrees`, `code_mode_host`, `plugin_sharing`, `remote_plugin` y
   `tool_suggest`. Y una versión futura de Codex puede traer funciones nuevas que se cuelen sin
   que nadie las revise.
2. **La rama de cancelación de `run_command` no recoge de forma acotada ni libera los pipes.** Al
   cancelar la llamada se hacía `killpg` y `communicate.cancel()`, pero el transporte del proceso
   quedaba abierto si un descendiente conservaba los pipes, y no se esperaba la recolección con el
   plazo corto que sí usa la rama de plazo vencido.

El nieto desasociado que sobrevive al plazo (hallazgo 3 de la revisión anterior) **se acepta como
riesgo residual documentado**: no se hace nada con él.

## What Changes

- Cada función habilitada de `codex features list` (que no esté `removed`) está clasificada
  explícitamente en el código: **desactivada** (`DISABLED_FEATURES`: ejecución de código o shell,
  lectura de disco o del workspace, subagentes o ampliación de herramientas, red, plugins, MCP) o
  **revisada y permitida** (`REVIEWED_ALLOWED_FEATURES`: interfaz, telemetría, transporte y
  compatibilidad, cada una con su motivo). Se amplía la lista de desactivadas.
- Un test falla si `codex features list` muestra una función habilitada que no está en ninguna de las
  dos listas (se salta si no hay binario; hay además un test unitario de la lógica con una salida
  falsa), para que una versión futura no incorpore herramientas sin revisión.
- La cancelación de `run_command` reutiliza `_reap_after_kill()` (protegida con `asyncio.shield` y
  con el plazo corto) antes de relanzar `CancelledError`, y libera el transporte.
- La documentación del riesgo residual de Codex (lista de denegación + sandbox + directorio vacío +
  entorno sin secretos) y del descendiente desasociado no promete que «no queden procesos».

## Capabilities

### New Capabilities

### Modified Capabilities
- `cli-review-agents`: «Solo lectura» (todas las funciones habilitadas de Codex clasificadas y
  vigiladas por un test) y «Espera acotada tras el plazo» (también al cancelar).

## Impact

- Código: `adapters/agents/codex_cli.py` y `adapters/subprocess_runner.py`.
- Tests: unitarios de la clasificación y de la cancelación; un test contra el `codex` real que no
  consume suscripción (`codex features list` no llama al modelo).
- Documentación: README, `docs/architecture.md`, `docs/testing.md` y `docs/flujo-duelo.html`.
