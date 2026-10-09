# Proposal

## Por qué

La ronda 1 dejó la API de lectura lista, pero el canal sigue siendo "tonto": no se puede
filtrar por estado ni buscar, un change no dice si su review va bien o mal sin abrir sus
reviews, una review fallida no se puede reintentar sin reenviar el commit (y una review
completada no debe relanzarse), el detalle no resume los hallazgos y `/ready` solo dice
"falla X" sin latencia ni diagnóstico. La ronda 2 de propuestas de Codex señaló cinco
huecos de backend que el frontend (filtro por estado, panel de hallazgos, botón de
reintento) necesita.

## Qué cambia

- **Filtros del canal**: `GET /projects/{slug}/changes` acepta `status` (repetible) y `q`
  (búsqueda por título, autor, SHA y ref, sin distinguir mayúsculas y con los comodines de
  `LIKE` escapados).
- **`review_status` agregado**: cada change (listado y detalle) incluye `review_status`
  (`pending`, `running`, `partial_failed`, `failed`, `completed`) calculado a partir de las
  reviews de su `run` actual frente a los agentes configurados.
- **`POST /changes/{id}/retry`**: arranca una nueva ejecución (`run + 1`) cuando la actual
  terminó con fallos (`failed` o `partial_failed`). Responde 202; 404 si el change no existe;
  409 si no hay nada que reintentar (pendiente, en curso o completada). Sin dobles arranques
  aunque lleguen dos peticiones a la vez. Requiere el token de ingesta (es una escritura).
- **Resumen de findings** en el detalle: `findings_summary` con `total` y `by_severity`
  (`bug`, `risk`, `improvement`, `nit`, `other`), sobre las reviews del `run` actual y con
  severidades normalizadas (los datos guardados no se tocan).
- **`GET /health/dependencies`**: estado de Postgres y Temporal con latencia en ms y un motivo
  de fallo de vocabulario cerrado (`timeout` o `error`), sin detalles de conexión.

Fuera de este change: cambios de frontend, detección de ejecuciones canceladas sin reviews
(requeriría consultar a Temporal), resumen de findings en el listado, autenticación de
lecturas y migraciones de esquema.

## Capacidades

### Nuevas capacidades

- `review-retry`: un cliente autenticado puede reintentar la review de un change cuya
  ejecución actual terminó con fallos.

### Capacidades modificadas

- `change-queries`: el canal se filtra por estado y texto; los changes exponen su estado de
  review agregado y el detalle un resumen de findings.
- `service-health`: nuevo diagnóstico de dependencias con latencia.

## Impacto

- Backend: `domain/review_status.py` (estado agregado, normalización de severidades),
  `application/` (puertos `ChangeRepository.list_for_project` con `status`/`q`/
  `expected_agents` y `advance_run`; casos de uso `retry_review`; `read_models`),
  `adapters/persistence/change_repository.py`, `adapters/orchestration/temporal_review_starter.py`
  (workflow id con sufijo `-r{run}` para `run > 1`), `entrypoints/api/` (schemas, routers
  `projects`, `changes`, `health`), `composition.py`, `docs/openapi.json`.
- Sin migración de esquema: `changes.run` ya existe; el filtro por estado agrega sobre `reviews`
  (índice `ix_reviews_change_id`).
- Contrato: campos nuevos en respuestas existentes (aditivos), parámetros opcionales nuevos y
  dos endpoints nuevos.
