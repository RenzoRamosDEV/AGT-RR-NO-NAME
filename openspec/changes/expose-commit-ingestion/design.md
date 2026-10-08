# Design

## Context

Hoy `ReviewCommitWorkflow` solo se arranca desde tests. La API (`entrypoints/api`) solo
tiene `/health`, sin configuración, sin base de datos y sin cliente de Temporal. Ver
`proposal.md - Por qué` para la motivación y la recomendación de Codex (ronda 9).

## Goals / Non-Goals

**Goals:**
- Un `curl` a `POST /ingest/commit` termina con dos `Review` de `FakeAgent` persistidas.
- Composición de dependencias en un único sitio (el entrypoint), sin lógica de
  infraestructura en `application/` ni `domain/`.
- Que reintentar la misma petición sea siempre seguro.

**Non-Goals:**
- Tokens por proyecto con hash, creación de proyectos por API, agentes reales, PRs.

## Decisions

**Token estático de configuración, no token por proyecto con hash (desviación del spec).**
El spec describe "token por proyecto guardado como hash". Eso exige que `Project` tenga
columna de hash y una vía para crear proyectos y emitir tokens - es el slice de `Project`,
no este. Mientras tanto, un `INGEST_TOKEN` de entorno comparado con `hmac.compare_digest`
da protección real (no hay endpoint inyectable sin credencial) con cero cambios de
esquema, y encaja con el alcance declarado del producto: herramienta personal en local,
API en `127.0.0.1`. Trade-off: un único secreto compartido por todos los proyectos y sin
rotación por proyecto. Se sustituye por tokens por proyecto en el slice de `Project`;
conviene registrarlo como ADR cuando eso ocurra.

**Persistir primero, arrancar el workflow después; ambos pasos idempotentes.** El caso de
uso `ingest_commit` llama a `ingest_change` (idempotente por clave natural) y luego a
`ReviewStarter.start`. Si Temporal está caído, la petición falla con 503 pero el `Change`
ya quedó guardado; reenviar la misma petición es seguro y arranca el workflow entonces.
Alternativa descartada: arrancar el workflow primero - dejaría un workflow sobre un change
que podría no existir.

**El workflow id determinista hace de segunda barrera de idempotencia.**
`commit-{project_id}-{head_sha}`: si ya existe, `WorkflowAlreadyStartedError` se trata
como éxito (la review ya está en marcha o terminó). No se confía solo en la idempotencia
de `Change` porque el `Change` puede existir sin workflow (caso del 503 anterior).

**`ReviewStarter` es un puerto; el adaptador de Temporal vive en `adapters/orchestration/`.**
Los adaptadores no pueden importar `workflows/` (capas hermanas), así que el contrato de
entrada del workflow (`ReviewCommitInput`) se mueve a `application/` (importable por
ambos lados) y `workflows/dto.py` lo reexporta. El adaptador arranca el workflow por su
nombre registrado (`"ReviewCommitWorkflow"`), igual que ya hacen los workflows con las
activities.

**`Project` mínimo y solo lectura (`ProjectRepository.get_by_slug`).** No se añade
creación. Para la verificación manual el proyecto se inserta con un `INSERT` SQL de una
línea; la creación real llega con el slice de `Project`.

**Configuración con `pydantic-settings`, validada al arrancar.** `Settings` lee
`DATABASE_URL`, `TEMPORAL_ADDRESS`, `INGEST_TOKEN` y `MAX_DIFF_CHARS` (por defecto
200 000). `INGEST_TOKEN` es obligatorio: sin él la API no arranca (falla rápido en vez de
quedar abierta por accidente). `create_app(settings)` recibe la configuración, de modo que
los tests construyen la app con valores propios sin tocar variables de entorno globales.

**Un único worker de desarrollo para ambas task queues (`entrypoints/worker.py`).** Con
`FakeAgent` no hay motivo para separar procesos todavía. El split real (`platform` en
Docker, `agents` en la máquina del desarrollador) llega con los agentes reales, cuando el
límite deje de ser decorativo. El worker usa los mismos nombres de cola que ya fija el
workflow (`platform`, `agents`).

**Recorte del diff en el caso de uso, no en el adaptador ni en la API.** Es una regla de
negocio (qué se guarda de un commit enorme), así que vive en `ingest_commit` y se prueba
sin HTTP ni base de datos.

## Risks / Trade-offs

- [Riesgo] Token estático compartido → Mitigación: API solo en `127.0.0.1` por defecto,
  comparación en tiempo constante, deuda anotada para el slice de `Project`.
- [Riesgo] Ciclo de vida del cliente de Temporal y del engine en el `lifespan` de FastAPI
  (fugas de conexión, arranque sin Temporal disponible) → Mitigación: el cliente de
  Temporal se conecta de forma perezosa en el primer uso y `/ready` expone el estado real;
  el engine se libera en el cierre del lifespan.
- [Riesgo] Sin worker corriendo, el workflow arrancado queda esperando → Mitigación:
  `just worker` y la verificación manual lo cubren; el test vertical levanta sus workers.
- [Riesgo] Cambiar de sitio `ReviewCommitInput` toca el slice anterior → Mitigación:
  reexport en `workflows/dto.py` y la suite existente de workflows lo protege.
- [Riesgo] Slice más ancho que los anteriores (HTTP + Temporal + DB a la vez) →
  Mitigación: `tasks.md` ordena por capas, cada grupo termina testeado antes del
  siguiente, y los tests de API usan fakes para ser rápidos; solo hay un test vertical.

## Open Questions

(ninguna - las decisiones de alcance quedan cerradas arriba)
