---
name: temporal-review
description: Revisa código de Temporal (workflows, activities, workers, DTOs, task queues, timeouts y reintentos) - determinismo y replay, versionado de workflows en vuelo, heartbeats, política de reintentos, idempotencia y compatibilidad de DTOs. Úsalo al tocar backend/src/duelo/workflows/, worker.py, adaptadores de orquestación o tests de workflows, o cuando pregunten "¿es seguro este cambio en el workflow?".
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(uv run pytest:*), Bash(just test-integration:*)
---

# Revisión de Temporal

Temporal re-ejecuta el código de un workflow desde su historial (replay). Un cambio que
altera la secuencia de comandos que el workflow emite rompe las ejecuciones en vuelo. Aquí
los errores se descubren tarde y en producción: revisa con más rigor que en código normal.

## Determinismo (código de `@workflow.defn`)

- Prohibido en workflows: `datetime.now()`, `random`, `uuid4()`, I/O, red, `asyncio.sleep`
  real (usa `workflow.sleep`), lectura de entorno, estado global mutable, imports pesados
  fuera de `workflow.unsafe.imports_passed_through()`. Todo eso va en activities.
- Orden de comandos estable: `asyncio.gather` sobre actividades es válido; iterar un `set`
  o un `dict` con orden no garantizado para decidir qué lanzar, no.
- Un workflow recibe un único DTO y devuelve un DTO/primitivo serializable.

## Cambios en workflows ya desplegados (versionado)

- Añadir, quitar o reordenar actividades, timers o hijos en un workflow que puede tener
  ejecuciones en vuelo exige `workflow.patched("id")` / `workflow.deprecate_patch` (o un
  workflow nuevo con otro nombre). Sin eso es `IMPORTANTE`, y `BLOQUEANTE` `CONFIRMADO`
  si hay un test de replay o un camino demostrado que falla.
- Cambiar el nombre registrado de un workflow o de una activity, o el nombre de su task queue
  (`platform` / `agents`), rompe a quien las llama por nombre de string: busca los
  llamadores con `Grep` (adaptador de arranque, workflows, tests, worker de desarrollo).
- Si el repo aún no tiene test de replay (`Replayer`), el hallazgo de versionado queda
  `PROBABLE` y se propone añadirlo con un historial capturado (`handle.fetch_history()`).

## DTOs y datos

- Por Temporal viajan IDs y primitivos, nunca el diff (límite de 2 MB por payload): un campo
  nuevo que pueda ser grande es `IMPORTANTE`. Hay regresión que lo fija: no la debilites.
- Compatibilidad hacia atrás: un campo nuevo en un DTO lleva valor por defecto (los
  historiales viejos no lo traen); quitar o renombrar un campo rompe el replay.

## Activities, timeouts y reintentos

- **Idempotencia:** reintentar es normal (at-least-once). Efectos con clave natural y
  `ON CONFLICT`; el éxito se persiste una vez aunque la activity corra dos.
- **`heartbeat_timeout` exige heartbeats:** una activity con `heartbeat_timeout` que no llama
  a `activity.heartbeat()` en su trabajo largo falla al agotarse ese plazo aunque siga viva.
  Comprueba que toda activity con `heartbeat_timeout` heartbea dentro del bucle de trabajo, o
  que el plazo no se fije.
- **Timeouts coherentes:** `start_to_close_timeout` ≥ duración realista del trabajo
  (un agente real tarda minutos, no milisegundos como `FakeAgent`).
- **Errores no reintentables** (`ApplicationError(non_retryable=True)`) para fallos de
  configuración o datos inexistentes; los transitorios se reintentan con límite
  (`maximum_attempts`) y backoff. Un reintento infinito sobre un error permanente es un bug.
- Un fallo de negocio esperado (el agente falló al revisar) se **registra como resultado**
  (`Review` fallida), no como excepción que reinicie la actividad.
- Los workflows de larga vida tienen límite de historial (continue-as-new si crecen).

## Arranque y deduplicación

- Workflow id **determinista** (`commit-{project_id}-{head_sha}`); `WorkflowAlreadyStartedError`
  se trata como éxito. La política `WorkflowIDReusePolicy` es explícita
  (`ALLOW_DUPLICATE_FAILED_ONLY`: una ejecución completada no se relanza, una fallida sí).
- El arranque desde la API ocurre **después** de persistir y es reintentable.

## Tests esperados

`tests/integration/workflows/` y `tests/integration/recovery/` con
`WorkflowEnvironment.start_time_skipping()`: paralelismo, fallo parcial, deduplicación por
id, worker ausente, fallo transitorio, reintentos acotados. Un cambio de workflow sin su
test es hallazgo de `test-coverage`.
