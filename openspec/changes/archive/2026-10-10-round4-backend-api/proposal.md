# Proposal

## Why

La API ya cubre ingesta, lectura, reintento y diagnóstico (rondas 1 a 3), y el frontend la consume
desde el navegador. Faltan los huecos para usarla de verdad: un navegador en otro origen no puede
llamarla (CORS), no hay forma de seguir una petición en los logs, el canal tiene un plan de consulta
que recorre todo el proyecto y toda la tabla `reviews` en cada página, `POST /ingest/*` y
`/changes/{id}/retry` no tienen ningún freno, y una review que nunca termina (worker caído,
ejecución perdida) se ve igual que una lenta.

## What Changes

- **CORS configurable**: `ALLOWED_ORIGINS` (lista explícita separada por comas; vacía por defecto =
  sin CORS). Un `*` se rechaza al arrancar. Sin credenciales (la API usa cabeceras de token).
- **Request ID y access log estructurado**: middleware que propaga un `X-Request-ID` entrante
  válido o genera uno, lo devuelve en la respuesta y emite una línea JSON por petición con método,
  ruta-plantilla, estado y latencia; nunca cuerpo, query ni cabeceras de token.
- **Índices y consulta del canal**: migración que sustituye los índices de `changes` y `reviews` por
  `(project_id, created_at, id)`, `(project_id, kind, created_at, id)` y
  `(change_id, run, status)`, y la consulta del canal pasa de agregar todas las reviews del
  proyecto a un `LEFT JOIN LATERAL` por change (medido con EXPLAIN: de ~58 ms a <1 ms con 60 000
  changes).
- **Rate limit** de `POST /ingest/commit`, `POST /ingest/pr` y `POST /changes/{id}/retry`: ventana
  deslizante en memoria por IP y por ruta, `429` con `Retry-After`, desactivable
  (`RATE_LIMIT_REQUESTS=0`).
- **Reviews atascadas**: `stale` (booleano de diagnóstico) en el listado y el detalle de changes
  cuyo estado agregado es `pending` o `running` desde hace más de `STALE_AFTER_SECONDS`. No relanza
  nada.
- Variables nuevas (`OPERATOR_TOKEN` incluida) documentadas en README y `docker-compose.yml`.

## Capabilities

### New Capabilities
- `api-cors`: orígenes permitidos para consumir la API desde un navegador.
- `request-observability`: identificador de petición y access log estructurado.
- `rate-limiting`: límite de peticiones en los endpoints de escritura.
- `stale-reviews`: marca de diagnóstico para changes cuya review lleva demasiado sin avanzar.

### Modified Capabilities

(ninguna: `stale` es un campo aditivo y vive en su propia capability)

## Impact

- `backend/src/duelo/config.py`, `entrypoints/api/` (app, middleware, routers de ingesta y
  changes, schemas), `application/` (puerto `RateLimiter`, `queries`, `read_models`),
  `domain/review_status.py`, `adapters/persistence/` (consulta del canal, modelos),
  `adapters/ratelimit/` (nuevo), `composition.py`.
- Migración Alembic nueva encadenada tras `c3f1a7d92b40`.
- `docs/openapi.json` (429, campo `stale`, cabecera `X-Request-ID`), `docs/architecture.md`,
  `docs/testing.md`, `README.md`, `docker-compose.yml`.
- Contrato aditivo: ningún campo ni código existente cambia.
