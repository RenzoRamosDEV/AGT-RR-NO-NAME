# Tasks

## 1. Compensación del fallo de infraestructura

- [x] 1.1 `record_review_infrastructure_failure` (activity) y helper por agente en `ReviewChangeWorkflow` con `workflow.patched`; verificar con tests de integración con Temporal de test (agente roto siempre → `failed` del roto y `completed` del otro; compensación repetida no duplica; agente desconocido sigue sin persistir nada; una historia anterior se reproduce con el workflow nuevo)
- [x] 1.2 Mensaje genérico sin texto de excepción; verificar con test unitario y de integración

## 2. Latidos

- [x] 2.1 Tarea periódica de `activity.heartbeat()` en `run_review`; verificar con test unitario (≥3 latidos con agente lento, la tarea se cancela al terminar o fallar, no-op fuera de una activity)

## 3. `run_started_at`

- [x] 3.1 Migración Alembic con backfill desde `created_at` y downgrade; verificar con test de migración arriba/abajo
- [x] 3.2 Dominio, modelo, repositorio, fakes y read models; `advance_run` guarda `started_at`; `is_stale` mide desde `run_started_at`; verificar con tests de dominio, de persistencia (`advance_run` actualiza la columna) y de API (un reintento limpia `stale`)

## 4. Cierre

- [x] 4.1 `just ci` en verde y mutación sobre los módulos tocados; docs (`architecture`, `testing`, guía) al día
