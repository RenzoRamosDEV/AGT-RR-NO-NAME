# Proposal

## Por qué

Tras las rondas 1 y 2 el canal y el detalle ya se pueden consultar, pero faltan datos que el
frontend necesita y que hoy obligan a cargar el diff entero o a adivinar: cuántos archivos y
líneas toca cada change, comparar agentes dentro de un repo, saber si una ingesta creó el
change o repitió uno existente, ver la línea de tiempo de un change y, para el operador,
inspeccionar la salida cruda de una review sin exponerla al público. La ronda 3 de propuestas
de Codex señaló estos cinco huecos de backend.

## Qué cambia

- **Resumen del diff**: cada change (listado y detalle) incluye `diff_summary` con
  `files_changed`, `additions`, `deletions` y la lista de archivos con sus líneas añadidas y
  borradas. Se calcula una vez al ingerir y se guarda; el listado sigue sin cargar el diff.
  Una migración añade la columna y rellena los changes existentes.
- **Estadísticas por proyecto**: `GET /stats/agents?project=owner/repo` limita las métricas a
  un proyecto (sin `project`, agregado global como hasta ahora; proyecto desconocido, 404).
- **`created` en la ingesta**: `POST /ingest/commit` y `POST /ingest/pr` responden además
  `created` (`true` si el change es nuevo, `false` si ya existía). El código de estado y la
  idempotencia no cambian.
- **Eventos de un change**: `GET /changes/{id}/events` devuelve, en orden, `change.created`,
  `review.completed` y `review.failed` con un payload reducido y estable (sin salida cruda ni
  mensajes de error).
- **Salida cruda de una review**: `GET /reviews/{id}/raw-output`, protegido con un token de
  operador distinto del de ingesta (`OPERATOR_TOKEN`). Sin token configurado el endpoint no
  existe (404) y los detalles públicos siguen sin exponer `raw_output`.

Fuera de este change: frontend, limitación de tasa, rotación de tokens, paginación de eventos
(un change genera un número pequeño y acotado) y exponer `OPERATOR_TOKEN` en `docker-compose.yml`.

## Capacidades

### Nuevas capacidades

- `change-events`: línea de tiempo auditable de un change.
- `review-raw-output`: descarga autenticada (operador) de la salida cruda de una review.

### Capacidades modificadas

- `change-queries`: `diff_summary` en listado y detalle; `GET /stats/agents` filtrable por proyecto.
- `commit-ingestion` y `pr-ingestion`: la respuesta indica si el change se creó.

## Impacto

- Backend: `domain/diff.py` (resumen puro del diff), `domain/change.py` (campo `diff_summary`),
  `application/` (puertos `ChangeEventRepository` y `ReviewRepository.get/agent_stats(project_id)`;
  casos de uso `change_events`, `review_raw_output`, `agent_stats` por proyecto; `IngestResult`
  vía `created`), `adapters/persistence/` (columna `changes.diff_summary`, repositorio de
  eventos, consulta de stats por proyecto), `entrypoints/api/` (schemas, routers `stats`,
  `changes`, `reviews`, `ingest`, `auth`), `config.py` (`operator_token`), `composition.py`,
  `docs/openapi.json`.
- Migración Alembic: `changes.diff_summary` (JSONB, con relleno de los existentes) e índice
  sobre `events ((payload->>'change_id'))`.
- Contrato: campos nuevos en respuestas existentes (aditivos), un parámetro opcional y dos
  endpoints nuevos.
