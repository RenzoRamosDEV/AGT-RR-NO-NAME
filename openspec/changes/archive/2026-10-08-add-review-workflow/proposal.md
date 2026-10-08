# Proposal

## Por qué

El criterio "hecho cuando" de Fase 1 ya quedó satisfecho con `add-change-ingestion`
(`ingest_change` persiste un `Change` y su evento atómicamente, probado con
testcontainers). Fase 2 del plan (`docs/spec/review-arena.md`) es "Workflows con agente
falso": *"un commit produce dos reviews de FakeAgent, y el test de fallo parcial pasa"*.
Esto exige introducir Temporal por primera vez en el proyecto (ver ADR 0001) y la entidad
`Review`, sin todavía depender de agentes reales ni del endpoint HTTP de ingesta.

Codex (ronda 8) recomendó separar el riesgo de Temporal del riesgo del entrypoint HTTP:
este change cubre solo el primer slice ("workflow mínimo sin HTTP todavía"), arrancando
el workflow directamente en los tests con un `change_id` ya persistido.

## Qué cambia

- Dominio (`domain/`): entidad `Review`, VO `Finding`, `ReviewResult` (lo que devuelve un
  agente: summary, score, findings - sin los campos de agente real como `prompt_version`
  o `model`, que llegan en Fase 3), evento `ReviewCompleted`/`ReviewFailed`.
- Aplicación (`application/`): puerto `ReviewAgent` (`async def review(change) -> ReviewResult`),
  puerto `ReviewRepository` (mismo patrón atómico + idempotente de `change-ingestion`,
  idempotente por `(change_id, agent, run)`), caso de uso `record_review`. Se amplía el
  puerto `ChangeRepository` con `get(change_id) -> Change | None` (requisito añadido a la
  capacidad `change-ingestion` existente - ver specs).
- Adaptadores (`adapters/`): `FakeAgent` (en memoria, sin red ni CLI real), modelos
  SQLAlchemy + migración para `reviews`, `SqlAlchemyReviewRepository`.
- Workflows (`workflows/`): `ReviewChangeWorkflow` (hijo) ejecuta dos `FakeAgent` en
  paralelo sobre el mismo `Change` y persiste una `Review` por cada uno;
  `ReviewCommitWorkflow` (padre) lo arranca una vez. Dos task queues (`platform` para
  cargar el change, `agents` para ejecutar la review) desde el día 1, tal como fija
  `openspec/config.yaml` - aunque `FakeAgent` no necesite correr fuera de Docker todavía,
  la frontera entre colas queda establecida ahora para no reescribirla en Fase 3.
- Tests: Temporal `WorkflowEnvironment.start_time_skipping()` (sin servidor real), cubre
  ejecución paralela y fallo parcial (un agente falla, el otro no bloquea).

Explícitamente fuera de este change (quedan para changes futuros):
`POST /ingest/commit` y cualquier entrypoint HTTP; `PullRequestWorkflow`,
`AnswerQuestionWorkflow`, debounce/señales; agentes reales (Claude/Codex); worker
`agents` corriendo de verdad fuera de Docker; comentarios en PRs; SSE/outbox leído por
nadie todavía; `prompt_version`/`agent_version`/`model`/Langfuse en `reviews`.

## Capacidades

### Nuevas capacidades

- `change-review`: el sistema puede ejecutar una review de un `Change` ya persistido
  mediante un workflow durable que corre agentes en paralelo (hoy, `FakeAgent`; más
  adelante, Claude Code y Codex), persistiendo una `Review` por agente de forma atómica
  e idempotente, y tolerando que un agente falle sin bloquear al otro.

### Capacidades modificadas

- `change-ingestion`: se añade el requisito de poder recuperar un `Change` ya persistido
  por su id (antes solo se podía ingerir, no consultar) - lo necesita la activity que
  carga el change antes de revisarlo.

## Impacto

- Código nuevo: `backend/src/review_arena/domain/review.py`,
  `backend/src/review_arena/application/record_review.py`,
  `backend/src/review_arena/adapters/agents/fake.py`,
  `backend/src/review_arena/adapters/persistence/review_repository.py` (+ modelos +
  migración), `backend/src/review_arena/workflows/review_change.py`,
  `backend/src/review_arena/workflows/review_commit.py`, dependencia nueva `temporalio`.
- Modificado: `application/ports.py` (añade `get` a `ChangeRepository`),
  `adapters/persistence/change_repository.py` (implementa `get`).
- Sin impacto todavía en la API HTTP, el frontend, ni en GitHub - nada de esto se dispara
  desde fuera de un test todavía.
- Done-when (criterio de la Fase 2 en el spec, acotado a este primer slice): un test con
  Temporal time-skipping demuestra que un `change_id` persistido produce dos `Review` de
  `FakeAgent`, y que el fallo de una no bloquea ni descarta la otra.
