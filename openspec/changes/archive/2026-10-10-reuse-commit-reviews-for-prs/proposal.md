# Proposal

## Why

Un commit y una PR cuyo último commit tiene el mismo SHA son dos `Change` distintos (la identidad
natural es `(proyecto, tipo, head_sha)`), así que cuando una PR tiene un solo commit los dos agentes
vuelven a revisar exactamente lo mismo que ya revisaron al hacer el commit. Con los agentes reales
(`claude` y `codex`) eso gasta dos veces la suscripción del usuario por el mismo diff.

## What Changes

- Al ingerir un change de tipo `pr` (por `POST /ingest/pr` y por la sincronización con `gh`, que pasan
  por el mismo caso de uso) se busca un change de tipo `commit` del **mismo proyecto**, con el **mismo
  `head_sha`** y el **mismo diff** almacenado. Si ese commit tiene una review `completed` de su run
  actual de **cada** agente esperado (`AGENT_NAMES`), la PR nace con esas reviews **copiadas**
  (`run` 1) y **no se arranca el workflow de Temporal**: no se gasta suscripción.
- La copia es atómica con el alta del change y de su evento `change.created`; cada review copiada
  genera un evento nuevo `review.reused`. Es idempotente: reenviar la PR no copia ni arranca nada, y
  dos ingestas simultáneas no duplican reviews.
- Si falta algún agente, alguna review falló, el diff es distinto (p. ej. una PR de varios commits) o el
  commit aún se está revisando, la PR se revisa con normalidad. Es un límite documentado.
- Cada review copiada guarda el change de origen en `reviews.reused_from_change_id` (nullable, FK con
  `ON DELETE SET NULL`; migración nueva con su `downgrade`). No se copia `raw_output`.
- API (todo aditivo): `reused_from` en las reviews del detalle y en las reviews ligeras del listado,
  `reused` en la respuesta de `POST /ingest/pr` y el evento `review.reused` en la línea de tiempo.
- Frontend (mínimo): una pill «Reutilizada del commit abc1234» en la review y sin orbe «está
  revisando…» para estos changes.

## Capabilities

### New Capabilities
- `review-reuse`: reutilización de las reviews completadas de un commit en la PR con el mismo SHA y el
  mismo diff, con copia atómica e idempotente, marca de origen y sin lanzar los agentes.

### Modified Capabilities
- `pr-ingestion`: la respuesta de `POST /ingest/pr` indica si las reviews se reutilizaron y una PR
  reutilizada no arranca workflow.
- `change-events`: la línea de tiempo expone el evento `review.reused`.
- `change-queries`: el detalle y las reviews ligeras del canal exponen `reused_from`.
- `frontend-shell`: la review reutilizada muestra su origen y no aparece como «revisando».

## Impact

- Backend: `domain` (`Review.reused_from_change_id`, evento `ReviewReused`, decisión pura
  `reviews_to_reuse`), `application` (`ingest_pr`, puerto `ChangeRepository`, lectura), `adapters/persistence`
  (modelo, repositorios, migración), esquemas de la API y `docs/openapi.json`.
- Frontend: tipos del cliente, `ReviewCard` y los mocks.
- Sin cambios en los workflows de Temporal, en los ids de workflow ni en las dependencias.
- Documentación: `docs/architecture.md`, `docs/testing.md`, `README.md` y la guía `docs/flujo-duelo.html`.
