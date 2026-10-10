# Proposal

## Why

Hoy toda review la hace el `FakeAgent`: devuelve siempre la misma nota (7) y un hallazgo `nit` sin
archivo ni línea. Todo el circuito (ingesta, Temporal, paralelismo, persistencia, UI) es real, pero
el contenido de la revisión es de mentira, y es lo que más falta para que Duelo sirva de algo.

El usuario ya tiene `claude` (Claude Code) y `codex` instalados y con la sesión iniciada en su
terminal y no quiere claves de API: los agentes deben apoyarse en esa sesión. El proyecto ya lo
prevé: el worker `agents` corre en la máquina del usuario, donde los CLI están autenticados, y los
agentes son adaptadores tras el puerto `ReviewAgent`.

## What Changes

- Dos adaptadores nuevos del puerto `ReviewAgent`: `ClaudeCliAgent` (`claude -p`) y
  `CodexCliAgent` (`codex exec`). Cada uno lanza el CLI como subproceso asíncrono, sin shell, en modo
  de **solo lectura**, le pasa el diff y pide una salida JSON conforme a un esquema (`summary`,
  `score` 0-10, `findings` con `severity`, `file`, `line` y `message`).
- El worker registra los agentes por nombre: `claude` y `codex` (sin distinguir mayúsculas) usan los
  CLI reales y cualquier otro nombre (`agent_1`, `agent_2`…) sigue siendo un `FakeAgent`, así que el
  valor por defecto de `AGENT_NAMES` y la CI no cambian. Para activarlos: `AGENT_NAMES=claude,codex`
  en la API **y** en el worker.
- Cada ejecución tiene un plazo propio (`AGENT_TIMEOUT_SECONDS`, 240 por defecto, menor que los 5
  minutos de la activity) y el worker limita cuántas corren a la vez (`AGENT_MAX_CONCURRENCY`, 2 por
  defecto) para que una ráfaga de commits no lance decenas de procesos.
- Si el proyecto es local y su carpeta existe, el agente trabaja con esa carpeta como directorio de
  trabajo (solo lectura) para dar contexto; si no, usa un directorio temporal vacío. La activity
  resuelve la ruta del proyecto del change sin cambiar los DTOs de Temporal (siguen viajando solo IDs).
- Cualquier fallo (binario ausente, sin sesión, plazo vencido, salida inválida) hace que el agente
  lance un error corto y saneado y la activity guarde una `Review(failed)`, como ya hace.
- Los binarios se localizan con `shutil.which` o con `CLAUDE_BIN` / `CODEX_BIN`; el modelo es
  opcional (`CLAUDE_MODEL` / `CODEX_MODEL`).

## Capabilities

### New Capabilities
- `cli-review-agents`: revisión de un change con los CLI de Claude Code y Codex ya autenticados, en
  solo lectura, con salida estructurada, plazo, concurrencia limitada y fallos controlados.

### Modified Capabilities

## Impact

- Código: `adapters/agents/` (módulos nuevos para los dos CLI, el prompt, el esquema y el parseo),
  `adapters/subprocess_runner.py` (entorno filtrado y límite de salida), `worker.py` (registro por
  nombre, semáforo y `max_concurrent_activities`), `config.py` (variables nuevas),
  `adapters/persistence/project_repository.py` (consulta de la ruta de un proyecto por id),
  `application/ports.py` y `workflows/activities.py` (resolución de la ruta sin tocar los DTOs).
- Configuración: `AGENT_TIMEOUT_SECONDS`, `AGENT_MAX_CONCURRENCY`, `CLAUDE_BIN`, `CODEX_BIN`,
  `CLAUDE_MODEL`, `CODEX_MODEL`. No hay claves de API.
- Operación: las reviews consumen la suscripción del usuario (Claude y Codex) y requieren estar
  logueado en ambos CLI en la máquina donde corre el worker. Documentado en README y `docs/`.
- API HTTP y contrato OpenAPI: sin cambios.
