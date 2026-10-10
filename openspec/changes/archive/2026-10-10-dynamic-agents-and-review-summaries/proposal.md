# Proposal

## Why

Al probar la UI contra la API real aparecieron tres desajustes entre lo que muestra el frontend y lo
que hace el backend (puntos D, E e I del diseño de Codex):

1. **«Ver respuestas» queda vacío (E).** El listado `GET /projects/{slug}/changes` no trae reviews,
   así que el panel de cada card del canal no tiene nada que mostrar con la API real; solo los datos
   de ejemplo las traían.
2. **Agentes fijos en la UI (I).** La interfaz escribe «Claude y Codex» a mano (canal, estado vacío,
   Ajustes) y `EXPECTED_AGENTS = 2`, mientras el backend usa `AGENT_NAMES` configurable
   (`agent_1`, `agent_2` por defecto).
3. **El detalle mezcla runs (D).** Tras un reintento el backend solo cuenta el `run` actual para el
   estado y los hallazgos, pero el detalle del frontend pinta las reviews de todos los runs juntas.

## What Changes

- **API (aditivo):** cada elemento del listado del canal lleva `reviews`, una lista ligera
  `{agent, status, score, duration_ms, run}` solo del `run` actual, sin resumen, hallazgos, error,
  salida cruda ni diff, obtenida con **una** consulta extra por página (sin N+1).
- **API (aditivo):** `GET /health/dependencies` añade `agent_names` (los de `AGENT_NAMES`).
- **UI:** las cards muestran esas reviews ligeras al instante; al abrir «Ver respuestas» se pide el
  detalle completo bajo demanda (con carga, error y reintento). El texto de los agentes sale de
  `agent_names` en vez de estar fijo y el estado agregado no depende de «2 agentes».
- **UI:** el detalle muestra y analiza solo el run actual; las reviews de runs anteriores quedan en
  secciones `<details>` colapsadas, agrupadas por run.

## Capabilities

### Modified Capabilities
- `change-queries`: el canal incluye las reviews ligeras del run actual.
- `service-health`: el diagnóstico informa de los agentes configurados.
- `frontend-shell`: respuestas del canal con la API real, agentes configurados y detalle por runs.

## Impact

- Código: `application/read_models.py`, `adapters/persistence/change_repository.py`,
  `entrypoints/api/{schemas,dependencies}.py`, `routers/health.py`, `composition.py`;
  `frontend/src` (`lib/api.ts`, `lib/runs.ts`, `lib/agents.ts`, `data/source.tsx`, canal, detalle,
  Ajustes, `ReviewCard`).
- Contrato: dos campos aditivos (`items[].reviews`, `agent_names`); `docs/openapi.json` regenerado.
- Sin migraciones: la consulta usa el índice `(change_id, run, status)` existente.
