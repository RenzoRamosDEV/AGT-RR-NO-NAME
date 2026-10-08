# Design

## Context

`add-change-ingestion` dejó `Change` persistible de forma atómica e idempotente. Fase 2
necesita, por primera vez en el proyecto, Temporal (ver ADR 0001 sobre por qué Temporal
frente a alternativas). Ver `proposal.md - Por qué` para la motivación completa; este
documento cubre solo el cómo.

Codex (ronda 8) propuso 5 formas de trocear Fase 2; se eligió su opción 1 (workflow
mínimo sin HTTP todavía), razonando que separa el riesgo de aprender el SDK de Temporal
del riesgo de exponerlo vía HTTP - exactamente el mismo principio que ya aplicamos en
`add-change-ingestion` separando dominio/aplicación de persistencia real.

## Goals / Non-Goals

**Goals:**
- Demostrar el patrón central de Fase 2: un `change_id` ya persistido produce dos
  `Review` de `FakeAgent` en paralelo, con fallo parcial tolerado, probado con Temporal
  time-skipping (sin servidor real).
- Establecer las dos task queues (`platform`, `agents`) desde ya, aunque `FakeAgent` no
  necesite correr fuera de Docker - es la frontera que sí importará en Fase 3.
- Mantener el patrón outbox: cada `Review` persistida escribe su evento en la misma
  transacción, igual que `change-ingestion`.

**Non-Goals (quedan para changes futuros):**
- Cualquier entrypoint HTTP (`POST /ingest/commit`, `/changes/{id}/rerun`, etc.).
- `PullRequestWorkflow`, `AnswerQuestionWorkflow`, debounce, señales de Temporal.
- Agentes reales (Claude Code vía Claude Agent SDK, Codex vía `codex exec`) y el worker
  `agents` corriendo de verdad en la máquina del desarrollador, fuera de Docker.
- `prompt_version`, `agent_version`, `model`, `langfuse_trace_id` en `reviews` - esos
  campos solo tienen sentido con agentes reales (Fase 3).
- Comentarios en PRs, SSE, votos, estadísticas.

## Decisions

**Dos agentes "fake" distintos (`agent_1`/`agent_2`), no uno solo ejecutado dos veces.**
El criterio de la Fase 2 dice "dos reviews de FakeAgent" (plural) - refleja la forma real
del producto (dos agentes configurados por proyecto, hoy Claude+Codex). Usar dos
instancias de `FakeAgent` con nombres distintos, en vez de un único "fake" ejecutado una
vez (como hace el modo demo del spec completo), deja el workflow ya preparado para que
Fase 3 solo tenga que cambiar qué implementa `ReviewAgent`, no cuántos corren.

**`ReviewAgent` con un solo método (`review`), no el `Protocol` completo del spec
(`review` + `answer` + `version`).** `answer()` pertenece al chat del canal (Fase 5,
`AnswerQuestionWorkflow`) y `version()` solo tiene sentido cuando hay versiones de agente
reales que registrar (Fase 3). Añadir ambos ahora sería diseñar para un caso de uso que
todavía no existe. Se amplía el `Protocol` cuando el change que los necesite llegue.

**`reviews` sin `prompt_version`/`agent_version`/`model`/`langfuse_trace_id` todavía.**
Esos campos describen agentes reales con prompts versionados y trazas de Langfuse;
`FakeAgent` no tiene ninguno de los dos. Añadirlos ahora con valores `NULL`/placeholder
sería modelar un dato que nada llena ni lee. Se añaden como migración incremental cuando
Fase 3 los necesite de verdad.

**`ChangeRepository.get()` se añade al puerto existente, no se crea un puerto nuevo de
"lectura".** La activity que carga el change antes de revisarlo necesita un único método
de consulta; un puerto `ChangeQueryRepository` separado (CQRS) sería la abstracción
prematura de siempre - un solo método no justifica una segunda interfaz. Se reconsiderará
si en el futuro la lectura y la escritura necesitan implementaciones realmente distintas
(por ejemplo, un read-model separado para el dashboard de Fase 6).

**Test con `WorkflowEnvironment.start_time_skipping()`, sin Temporal real ni Docker
Compose en esta primera prueba.** El SDK de Temporal trae un entorno de test efímero que
no necesita el servidor de `docker-compose.yml`; se usa para probar paralelismo y fallo
parcial de forma rápida y determinista. La verificación manual contra un Temporal real
(vía `just dev`, que ya lo incluye en el perfil `infra` desde Fase 0) es parte de las
tareas de este change, pero el test automatizado no depende de levantar contenedores.

**Dos task queues desde ya (`platform` para cargar el change, `agents` para ejecutar la
review), aunque ambas corran en el mismo proceso de test/desarrollo por ahora.** Es una
decisión ya tomada y documentada como binding en `openspec/config.yaml`; introducirla
ahora con `FakeAgent` evita reescribir la frontera entre colas cuando Fase 3 necesite que
el worker `agents` corra de verdad fuera de Docker.

**`ReviewActivities` recibe fábricas de repositorio inyectadas, no instancia
`SqlAlchemy*Repository` directamente.** *Descubierto durante la implementación (tarea
5.1):* `import-linter` rechazó `workflows/activities.py` importando
`adapters/persistence/*` - `entrypoints`, `adapters` y `workflows` son capas hermanas en
la regla de capas (`domain <- application <- adapters/entrypoints/workflows`), ninguna
puede importar a otra. `ReviewActivities` ahora recibe `change_repository` y
`review_repository` como `Callable[[AsyncSession], Puerto]` (la clase concreta del
adaptador, p. ej. `SqlAlchemyChangeRepository`, ya es ese callable); quien construye la
instancia (el test, y más adelante el entrypoint del worker `agents`) es quien conoce
ambas capas y hace la composición. `workflows/` queda dependiendo solo de
`application.ports` y `application.record_review`, igual que ya hacía `entrypoints/api`.

## Risks / Trade-offs

- [Riesgo] Primera vez que el proyecto usa Temporal - curva de aprendizaje del SDK
  (workflows deterministas, activities, `workflow.execute_activity`) → Mitigación: este
  slice se mantiene deliberadamente angosto (sin HTTP, sin PR workflow, sin agentes
  reales) precisamente para aislar ese riesgo, tal como recomendó Codex.
  Replay/`workflow.patched()` para cambios de código no se cubren todavía - solo son
  relevantes cuando haya workflows en curso en producción, y este slice no lo despliega.
- [Riesgo] Dos task queues sin que nada las diferencie todavía (ambas en el mismo worker
  de test) puede parecer ceremonia innecesaria → Mitigación: aceptado a propósito, ver
  Decisions - el costo es bajo (un parámetro `task_queue=` por activity) y evita una
  migración de infraestructura en Fase 3.
- [Riesgo] `reviews` sin los campos de agente real puede obligar a una migración
  adicional pronto (Fase 3) → Mitigación: aceptado - es más barato añadir columnas
  cuando haya algo real que guardar en ellas que diseñarlas ahora a ciegas.

## Open Questions

(ninguna - el alcance queda cerrado arriba; las dudas de implementación concretas del SDK
de Temporal se resuelven durante `apply`, no cambian el alcance ni las specs)
