# Design

## A. Fallo de infraestructura como review fallida

**Causa.** `asyncio.gather` en `ReviewChangeWorkflow` propaga la `ActivityError` de la activity que
agota sus reintentos. Esa excepción no pasa por `record_review_failure` (que solo cubre el fallo de
`agent.review()` capturado dentro de la activity), así que no hay fila ni evento.

**Decisión.** Cada agente se ejecuta con un helper `_review_one` que envuelve
`execute_activity("run_review", ...)`. Si lanza `ActivityError`:

- si la causa es un `ApplicationError` **no reintentable** (agente desconocido, change inexistente)
  se relanza tal cual: es un error de configuración, no se registra ninguna review (así no contamina
  estadísticas) y se mantiene el comportamiento actual;
- en cualquier otro caso se ejecuta `record_review_infrastructure_failure` (misma cola `agents`,
  reintentos propios) y se devuelve `RunReviewResult(status="failed", review_id)`.

La compensación es idempotente porque `reviews` tiene `UNIQUE(change_id, agent, run)` con
`ON CONFLICT DO NOTHING` y el evento se escribe solo si hubo inserción: repetirla (o que `run_review`
llegara a persistir justo antes) no duplica fila ni evento.

**Mensaje guardado.** Es una cadena genérica y estable
(`Fallo de infraestructura: la review no pudo completarse tras varios intentos`); no incluye
`str(exc)` ni la traza, que pueden arrastrar rutas, SQL o credenciales. El detalle queda en el
historial de Temporal.

**Cada agente es independiente.** Como el helper no relanza, `asyncio.gather` ya no cancela a los
hermanos cuando uno falla.

**Versionado.** Un workflow en vuelo que ya ejecutó `run_review` con el código anterior no debe
romper el replay. La rama nueva (captura de `ActivityError` y compensación) va bajo
`workflow.patched("compensate-infra-failure")`: las ejecuciones nuevas la toman; las que se
reproducen sin el marcador siguen el camino antiguo (`gather` sin captura). El parche se puede
retirar con `workflow.deprecate_patch` cuando no queden ejecuciones anteriores.

**Cancelación.** Una `CancelledError` del workflow no se captura (no es `ActivityError`).

## B. Latidos

`run_review` lanza una tarea de `asyncio` que llama a `activity.heartbeat(...)` de inmediato y luego
cada `HEARTBEAT_INTERVAL` (10 s, un tercio del `heartbeat_timeout` de 30 s) mientras corre
`agent.review()`. La tarea se cancela en un `finally`. Limitación: si un adaptador de agente bloquea
el event loop (I/O síncrona), la tarea no late; los agentes deben usar I/O asíncrona.

## C. `run_started_at`

- Columna `changes.run_started_at timestamptz NOT NULL`. La migración la añade con
  `server_default=now()` (igual que `created_at`, así el modelo y el esquema coinciden) y rellena las
  filas existentes con `created_at` (el único dato disponible; un change reintentado antes de esta
  versión pierde la precisión del reintento). Downgrade: elimina la columna.
- `Change.new` fija `run_started_at = created_at`. `advance_run(change_id, from_run, started_at)`
  recibe el instante del caso de uso (reloj inyectado, determinista en tests) y lo guarda junto con
  `run + 1` en el mismo `UPDATE` compare-and-swap.
- `is_stale(status, run_started_at, ...)` mide desde ahí. Si `starter.start()` falla, `advance_run`
  no se ejecuta y el reloj no cambia (el reintento se puede repetir).
- El cursor del canal sigue ordenando por `created_at`: `run_started_at` solo alimenta `stale`.
