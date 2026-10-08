# Design

## Context

Backend hoy: paquetes `domain/`, `application/`, `adapters/`, `workflows/`, `entrypoints/`
existen pero están vacíos salvo el endpoint `/health` (Fase 0). No hay Postgres en uso
todavía por la API (solo disponible en Docker Compose para fases futuras), ni SQLAlchemy,
ni Alembic configurados. Ver `proposal.md - Por qué` para la motivación; este documento
cubre solo el cómo.

Codex propuso 5 formas de trocear la Fase 1; se eligió la síntesis de sus propuestas 1 y 2:
alcance de la propuesta 1 (`Change` mínimo + `ingest_change` + outbox desde el día 1, sin
`Review`/`Vote`/agentes/Temporal/API/auth) con el orden interno de la propuesta 2 (dominio
puro con fakes primero, adaptador SQLAlchemy/Alembic/testcontainers después).

## Goals / Non-Goals

**Goals:**
- Un caso de uso `ingest_change` ejecutable y testeado, con y sin Postgres real, que
  persiste un `Change` y su evento `change.created` de forma atómica e idempotente por
  `(project_id, kind, head_sha)`.
- Dejar el patrón outbox (escritura del evento en la misma transacción que el estado) ya
  resuelto a nivel de adaptador, para que Fase 2 solo tenga que leer de `events`, no
  rediseñar cómo se escribe.
- Mantener la regla de capas (`domain <- application <- adapters`) intacta: `domain/` y
  `application/` no importan SQLAlchemy ni nada de `adapters/`.

**Non-Goals (quedan para changes futuros, no se diseñan aquí):**
- Exponer esto vía HTTP (`POST /ingest/commit`). Se añade cuando Fase 2 necesite disparar
  `ReviewCommitWorkflow` desde ahí - acoplar el endpoint a un workflow que todavía no existe
  sería construir una pieza a medias.
- `Review`, `Vote`, `Message`, agentes, Temporal.
- `Project` como agregado rico (settings, token de ingesta, rutas ignoradas). Aquí `Project`
  es deliberadamente mínimo (solo lo necesario para la FK y la unicidad natural); crecerá
  cuando la ingesta real (webhooks/hook local) necesite su token y sus ajustes.
- LISTEN/NOTIFY y SSE: el evento se escribe, pero nada lo consume todavía.

## Decisions

**Un solo puerto (`ChangeRepository`), no `ChangeRepository` + `EventPublisher`
separados.** La propuesta inicial mencionaba un puerto de publicación de eventos aparte;
se descarta aquí. Con un único agregado (`Change`) escribiendo un único tipo de evento, un
puerto de publicación separado no tendría ninguna responsabilidad real que
`ChangeRepository.add()` no tenga ya (ambas escrituras viven en la misma transacción de
todos modos). Se introducirá `EventPublisher` como puerto propio cuando un segundo
agregado (`Review`, `Vote`) necesite emitir eventos y compartir esa lógica - no antes.
Alternativa descartada: diseñarlo ya "por si acaso", que es exactamente el tipo de
abstracción prematura que el proyecto quiere evitar.

**Idempotencia resuelta con una restricción `UNIQUE` en Postgres, no con un `SELECT`
previo.** El caso de uso no hace `find_by_natural_key` y luego `insert` (hay una carrera
entre ambas operaciones bajo concurrencia); el adaptador intenta el `INSERT` y captura la
violación de unicidad de Postgres (`(project_id, kind, head_sha)`) para decidir que la
ingesta ya existía y devolver el `Change` existente sin crear un segundo evento. Alternativa
descartada: `SELECT ... FOR UPDATE` antes de insertar - añade una vuelta extra a la base de
datos para resolver algo que la restricción ya resuelve de forma atómica.

**`Project` mínimo (solo `id`, `slug`) en esta migración, no el modelo completo del spec.**
Evita diseñar `settings` (jsonb), `ingest_token_hash` y demás antes de que algo los use
de verdad. La migración de este change añade una fila de `Project` de prueba únicamente
para los tests de integración; no hay todavía forma de crear proyectos desde fuera.

**Dominio probado con un `FakeChangeRepository` en memoria antes de escribir SQLAlchemy.**
`ingest_change` (el caso de uso) se implementa y se testea completo contra el puerto, con
un fake que vive en `tests/`, antes de escribir el adaptador real. Esto obliga a que el
puerto esté bien diseñado (expresado en términos del dominio, no de SQL) antes de que
SQLAlchemy entre en escena. Solo al final se añade un test de integración con
`testcontainers` que ejercita el adaptador real contra un Postgres real.

**Alembic desde esta migración, no "ya lo añadiremos".** Una sola migración inicial crea
`projects`, `changes`, `events` con sus índices (incluida la constraint `UNIQUE` de
idempotencia). Cualquier cambio de esquema futuro parte de una migración real desde el
primer commit de Fase 1, no de un `create_all()` informal.

**`testcontainers` solo para el test de integración del adaptador, no para los tests del
caso de uso.** El caso de uso (`ingest_change`) se prueba con el fake - rápido, sin Docker.
Solo el test del adaptador SQLAlchemy levanta un Postgres real vía `testcontainers`, que es
exactamente donde aporta valor (probar que el `INSERT` + la constraint `UNIQUE` + la
transacción se comportan como se diseñó contra un Postgres real, no contra SQLite u otro
sustituto).

## Risks / Trade-offs

- [Riesgo] Introducir SQLAlchemy async + Alembic en el mismo change que el dominio puede
  diluir el corte hexagonal si no se disciplina el orden → Mitigación: `tasks.md` ordena
  explícitamente dominio → puerto → caso de uso con fake → adaptador SQLAlchemy, cada grupo
  termina en algo testeado antes de avanzar al siguiente.
- [Riesgo] `testcontainers` en CI añade tiempo y necesita Docker-en-Docker en el runner →
  Mitigación: por ahora el test de integración se ejecuta localmente (`uv run pytest`, el
  desarrollador tiene Postgres/Docker); añadirlo al job `backend-test` de CI es una tarea
  explícita de este change (`tasks.md`), no una sorpresa de scope.
- [Riesgo] Capturar la violación de unicidad de Postgres acopla el adaptador a un código de
  error específico de `asyncpg`/`psycopg` → Mitigación: se aísla en un único punto del
  adaptador (un `try/except` alrededor del `INSERT`), documentado con un comentario que
  explica qué código de error se captura y por qué.

## Open Questions

(ninguna - el alcance y las decisiones de esta fase quedan cerrados arriba)
