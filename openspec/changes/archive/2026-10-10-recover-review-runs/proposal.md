# Proposal

## Why

Tres defectos reales del flujo de reviews, detectados al revisar el flujo de punta a punta:

1. **Change atascado sin salida.** Si una activity `run_review` agota sus 3 intentos por un fallo de
   infraestructura, no se guarda ninguna `Review`: el workflow termina `Failed`, pero el change se
   queda `pending` o `running` y esos estados no son reintentables (`POST /changes/{id}/retry`
   responde 409). Solo el diagnóstico `stale` lo señala.
2. **Heartbeat sin latidos.** El workflow declara `heartbeat_timeout=30s`, pero ninguna activity
   llama a `activity.heartbeat()`. Con un agente real que tarde más de 30 s, Temporal declararía
   timeout y reintentaría sin motivo.
3. **`stale` mide desde la creación del change.** Tras un reintento sobre un change antiguo, el
   nuevo `run` aparece `stale` de inmediato aunque acabe de arrancar.

## What Changes

- Una activity compensatoria idempotente `record_review_infrastructure_failure` persiste una
  `Review(failed)` (con un mensaje genérico, sin texto de excepciones internas) cuando `run_review`
  agota sus reintentos. El workflow la ejecuta por agente sin cancelar a los demás. El change pasa a
  `failed` o `partial_failed` y ya es reintentable. El cambio de comportamiento del workflow va
  protegido con `workflow.patched` para no romper ejecuciones en vuelo.
- `run_review` emite latidos (`activity.heartbeat()`) de forma periódica mientras el agente trabaja.
- `changes.run_started_at` (migración con backfill desde `created_at`): lo fija la ingesta y lo
  refresca `advance_run`; `stale` se mide desde ahí.

## Capabilities

### Modified Capabilities
- `change-review`: fallo de infraestructura registrado como review fallida; latidos.
- `stale-reviews`: `stale` se mide desde el inicio del `run` actual.
- `review-retry`: un reintento reinicia el reloj de `stale`.

## Impact

- Código: `workflows/review_change.py`, `workflows/activities.py`, `workflows/dto.py`,
  `application/record_review.py`, `domain/change.py`, `domain/review_status.py`,
  `application/queries.py`, `application/retry_review.py`,
  `adapters/persistence/{models,change_repository}.py`, puerto `ChangeRepository.advance_run`,
  composición y una migración Alembic nueva.
- API: sin cambios de contrato (`stale` sigue siendo un booleano).
- Base de datos: columna `changes.run_started_at timestamptz NOT NULL`; backfill desde `created_at`.
- Docs: `docs/architecture.md`, `docs/testing.md` y las frases afectadas de `docs/flujo-duelo.html`.
