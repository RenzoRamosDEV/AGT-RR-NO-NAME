# Proposal

## Por qué

Fase 2 ya tiene el workflow interno (`ReviewCommitWorkflow` con `FakeAgent`) pero solo se
puede disparar desde un test: todavía no existe el flujo "desde fuera" del spec
(*"Haces `git commit`; el hook envía el diff a `POST /ingest/commit`..."*). Codex (ronda 9)
recomendó completar ese puente antes de gastar tiempo en agentes reales (Fase 3): primero
se cierra la composición API → Postgres → Temporal con agentes falsos, que son baratos y
deterministas. PRs, debounce y webhooks quedan para Fase 5, como indica el spec.

## Qué cambia

- **`POST /ingest/commit`**: recibe un commit de un proyecto existente, lo persiste con
  `ingest_change` y arranca `ReviewCommitWorkflow` con workflow id determinista
  `commit-{project_id}-{head_sha}`. Responde `202` con el id del change.
- **Autenticación mínima de ingesta**: cabecera `X-Ingest-Token` comparada en tiempo
  constante contra un token de configuración. Sin token válido: `401`, sin efectos.
- **Idempotencia de extremo a extremo**: reenviar el mismo commit devuelve el mismo
  change, no duplica `Change` ni evento, y no arranca una segunda review.
- **Diff acotado**: un diff por encima del máximo configurado se guarda recortado con
  `diff_truncated = true` (mitigación del spec contra diffs enormes).
- **`GET /ready`**: 200 solo si Postgres y Temporal son alcanzables; 503 indicando cuál
  falla. Es el contrato que quedó diferido desde Fase 0 y ahora tiene dependencias reales
  que comprobar. `/health` no cambia.
- **Configuración 12-factor** (`config.py` con `pydantic-settings`): `DATABASE_URL`,
  `TEMPORAL_ADDRESS`, `INGEST_TOKEN`, límite de diff. Era la deuda "config.py cuando entren
  DB/Temporal reales" anotada en rondas anteriores.
- **Composición real de dependencias** en el entrypoint de la API (sesiones SQLAlchemy,
  repositorios, cliente de Temporal) y un **entrypoint de worker de desarrollo**
  (`just worker`) que ejecuta ambas task queues con `FakeAgent`, para poder ver el flujo
  completo con `curl`.
- Puerto `ProjectRepository` (`get_by_slug`) y puerto `ReviewStarter` (arrancar la review
  de un change), con sus adaptadores SQLAlchemy y Temporal.

- **Tests dependientes de la API** (contratos, autenticación y autorización, seguridad de
  API, E2E por HTTP y carga), heredados del checklist de `strengthen-test-suite`: ver
  `docs/testing.md` y el grupo 8 de `tasks.md`.

Fuera de este change: tokens por proyecto con hash y creación de proyectos por API
(slice de `Project`), agentes reales, PRs/webhooks de GitHub, SSE, frontend, cliente
TypeScript generado, workers separados en Docker (`platform`) y local (`agents`).

## Capacidades

### Nuevas capacidades

- `commit-ingestion`: un cliente local (el hook post-commit) puede enviar un commit por
  HTTP y el sistema lo persiste y dispara su review sin duplicar trabajo, rechazando las
  peticiones no autorizadas.

### Capacidades modificadas

- `service-health`: se añade el requisito de readiness (`GET /ready`) que comprueba
  Postgres y Temporal.

## Impacto

- Backend: `config.py`, `domain/project.py`, `application/` (puertos `ProjectRepository`
  y `ReviewStarter`, caso de uso `ingest_commit`), `adapters/persistence/project_repository.py`,
  `adapters/orchestration/` (starter de Temporal), `entrypoints/api/` (app con lifespan,
  router de ingesta, schemas, auth, readiness), `entrypoints/worker.py`, `justfile`.
- Dependencias nuevas: `pydantic-settings`.
- Sin migración de esquema: `projects`, `changes`, `events` y `reviews` ya existen.
- Done-when (criterio de Fase 2 del spec, ya cerrado de punta a punta): un test vertical
  (ASGI + Postgres real + Temporal de test) demuestra que `POST /ingest/commit` termina
  con dos `Review` de `FakeAgent` persistidas, y una verificación manual con
  `just dev` + `just worker` + `curl` lo confirma contra Temporal real.
