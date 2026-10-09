# Proposal

## Why

Las rondas 1-3 dejaron la interfaz usable con datos de ejemplo y un cliente de la API de lectura,
pero quedan huecos de conexión con el backend: las estadísticas siguen siendo un mock, el canal
filtra solo lo ya cargado (con paginación el filtro engaña), no se puede reintentar una review
fallida, Ajustes no enseña el estado real del servidor y las cards ocultan los datos de cada
review (run, duración, nota, error). `round2-backend-api` ya define el contrato para todo ello
(`status`/`q`, `review_status`, `POST /changes/{id}/retry`, `GET /health/dependencies`) y
`round1-backend-api` el de `GET /stats/agents`. Esta ronda 4 (propuesta por Codex) los conecta.

## What Changes

- **Estadísticas reales:** la tabla consume `GET /stats/agents` (total, completadas, fallidas,
  duración y nota medias) con estados de carga, error y vacío.
- **Filtros del canal en servidor:** búsqueda, tipo, estado y cursor viajan como
  `q`/`kind`/`status`/`cursor`; el cliente deja de filtrar lo ya cargado.
- **Reintentar review:** botón en el detalle con fallo agregado (`failed`/`partial_failed`) que
  llama a `POST /changes/{id}/retry` con un token que el usuario escribe y que solo vive en
  memoria; trata 202, 401, 404, 409 y 503.
- **Diagnóstico real en Ajustes:** proyectos vigilados desde `GET /projects` y estado de Postgres
  y Temporal desde `GET /health/dependencies`, con latencia y degradación.
- **Metadatos de review en las cards:** run, duración, nota y error sanitizado.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: estadísticas reales, filtros del canal en servidor, reintento de review,
  diagnóstico en Ajustes y metadatos de review.

## Impact

- `frontend/src`: `lib/api.ts` (`DataSource` gana `agentStats`, `health` y `retry`; `changes` gana
  `q`/`status`), `data/mock.ts` y `data/source.tsx` (la fuente de ejemplo respeta los mismos
  filtros y estado agregado), `lib/` nuevos (`channelQuery`, `reviewStatus`, `format`,
  `sanitize`, `ingestToken`), `features/**`, `components/ReviewCard.tsx`, estilos en `index.css`.
- Se elimina `lib/changeFilters.ts` (el filtrado pasa al servidor); `lib/search.ts` queda solo para
  la fuente de ejemplo, con la misma regla que `q` del servidor (incluye el ref).
- Sin dependencias nuevas y sin cambios de backend.
