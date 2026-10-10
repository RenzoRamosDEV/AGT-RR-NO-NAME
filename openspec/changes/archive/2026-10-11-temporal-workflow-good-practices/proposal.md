# Proposal

## Why

Se auditó la orquestación de Duelo contra el estándar de buenas prácticas de Temporal
(`Preguntas/temporal-buenas-practicas.md`, derivado de la documentación oficial). Los workflows,
activities y DTOs ya cumplen lo esencial (determinismo, DTO único, parches de replay, idempotencia,
timeouts, heartbeat, compensación, replay tests), pero la **operación del worker** no: no se apaga
de forma ordenada, no expone métricas, no admite otro namespace y los nombres de las task queues
están repetidos como literales. Además, la decisión de versionado (parches frente a Worker
Versioning) no está escrita, así que cada cambio de workflow la vuelve a discutir.

## What Changes

- **Apagado ordenado del worker.** `SIGTERM`/`SIGINT` dejan de matar el proceso en seco: el worker
  deja de aceptar tareas, da un plazo de gracia a las activities en curso (cancelación que mata el
  CLI del agente) y sale con código 0. Un agente a medias se reintenta por la política normal.
- **Namespace configurable.** `TEMPORAL_NAMESPACE` (por defecto `default`) usado por la API y el
  worker, para separar entornos sin tocar código.
- **Métricas del SDK, opcionales.** `TEMPORAL_METRICS_ADDRESS` (p. ej. `127.0.0.1:9464`) hace que el
  worker exponga en Prometheus las métricas del SDK (latencia schedule-to-start, slots libres,
  fallos de peticiones). Sin la variable no cambia nada. Se documentan las alertas mínimas.
- **Política de reintentos explícita y compartida.** `backoff_coefficient` 2, `maximum_interval`
  1 min y 3 intentos, definidos en un solo sitio junto a los plazos (hoy el máximo entre intentos
  es implícito, 100 s).
- **Task queues como constantes compartidas** (`platform`, `agents`) en lugar de cinco literales.
- **ADR de versionado.** Se documenta que Duelo versiona con `workflow.patched` + replay tests
  (semántica *Auto-Upgrade*) y por qué no adopta Worker Versioning.
- **Documentación.** Matriz de cumplimiento del estándar (qué se cumple, dónde, y qué no aplica
  a un despliegue local de un solo usuario), variables nuevas y checklist de PR ampliado en la
  skill `temporal-review` (Continue-As-New, métricas, apagado).

Sin cambios en API, base de datos, frontend ni en los ids o el historial de los workflows.

## Capabilities

### New Capabilities
- `worker-operations`: cómo se opera el worker de Temporal: apagado ordenado, namespace y
  métricas expuestas.

### Modified Capabilities
- `change-review`: se añade el requisito de la política de reintentos de las activities de review
  (intentos, backoff y espera máxima acotada).

## Impact

- Código: `worker.py`, `config.py`, `adapters/orchestration/temporal_client.py`, `composition.py`,
  `workflows/review_change.py`, `adapters/orchestration/temporal_review_starter.py`,
  `application/review_timeouts.py` y un módulo nuevo de constantes en `application/`.
- Tests: unitarios de configuración, apagado por señal y política; integración con Temporal de
  test para el apagado con una activity en curso y para el endpoint de métricas.
- Docs: `docs/adr/0007-…`, `docs/architecture.md` (variables, operación, enlace a la matriz),
  `docs/temporal-buenas-practicas.md` (matriz), `docs/testing.md`,
  `.claude/skills/temporal-review/SKILL.md`.
- Dependencias: ninguna nueva (`temporalio` ya trae Prometheus; `httpx` ya es dependencia de
  desarrollo para el test del endpoint).
