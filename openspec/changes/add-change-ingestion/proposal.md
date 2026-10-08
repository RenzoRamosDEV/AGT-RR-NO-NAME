# Proposal

## Por qué

Fase 0 dejó un esqueleto sin dominio: `backend/src/review_arena/{domain,application,adapters}`
existen como paquetes vacíos. Fase 1 del plan (`docs/spec/review-arena.md`) exige el primer
corte real de dominio y persistencia, con criterio de aceptación explícito: *"`ingest_change`
guarda el change y su evento en una transacción, probado con testcontainers"*. Sin esto, no
hay nada que los workflows de Temporal (Fase 2) puedan invocar, ni nada que persista lo que
los hooks/webhooks de ingesta (Fase 2+) van a enviar.

## Qué cambia

Primer slice vertical de Fase 1, acotado deliberadamente para no abrir más superficie de la
necesaria (ver `design.md` para el porqué de cada corte):

- Dominio puro (`domain/`): entidad `Change` con sus value objects mínimos (`ChangeKind`:
  `commit` | `pr`, estado inicial), sin dependencias de infraestructura.
- Aplicación (`application/`): puerto `ChangeRepository` (su método `add` persiste el
  `Change` y su evento `change.created` en una sola transacción - ver `design.md` sobre por
  qué no se introduce todavía un puerto `EventPublisher` separado), caso de uso
  `ingest_change`. Probado primero con un adaptador falso en memoria.
- Adaptadores (`adapters/persistence/`): modelos SQLAlchemy 2.0 async para `projects`,
  `changes`, `events`; repositorio concreto; migración Alembic inicial.
- Tests de integración con `testcontainers` (Postgres real) que verifican que `ingest_change`
  persiste el `change` y su `event` atómicamente (si uno falla, no se guarda el otro).

Explícitamente fuera de este change (quedan para changes posteriores, ver `design.md`):
`Review`, `Vote`, `Message`; agentes; Temporal; endpoint HTTP `POST /ingest/commit` (la
exposición HTTP llega cuando Fase 2 necesite disparar el workflow desde ahí); autenticación
por token; deduplicación de PRs/debounce; LISTEN/NOTIFY y SSE.

## Capacidades

### Nuevas capacidades

- `change-ingestion`: el sistema puede recibir los datos de un cambio (commit o PR) y
  persistirlo junto con su evento de dominio de forma atómica, de modo que ningún evento se
  pierda y ninguna escritura quede a medias. Capacidad durable que seguirá creciendo
  (deduplicación, más tipos de evento, reintentos) en changes futuros sin cambiar su
  contrato básico.

### Capacidades modificadas

(ninguna)

## Impacto

- Código nuevo: `backend/src/review_arena/domain/change.py` (entidad + VOs),
  `backend/src/review_arena/application/ports.py` (`ChangeRepository`, `EventPublisher`),
  `backend/src/review_arena/application/ingest_change.py` (caso de uso),
  `backend/src/review_arena/adapters/persistence/` (modelos SQLAlchemy, repositorio,
  engine/sesión), `backend/alembic/` (migración inicial), tests unitarios (fakes) e
  integración (testcontainers).
- Dependencias nuevas: `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `testcontainers[postgres]`
  como dev-dependency.
- Sin impacto todavía en la API HTTP, Temporal, ni en el frontend - ninguno de esos
  consume todavía esta capacidad.
- Done-when (criterio de la Fase 1 en el spec): un test con testcontainers demuestra que
  `ingest_change` guarda el `change` y su `event` en una sola transacción.
