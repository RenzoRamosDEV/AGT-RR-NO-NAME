# Arquitectura

Monolito modular con tres procesos (API, worker `platform`, worker `agents`) sobre una
arquitectura hexagonal: el dominio (`Change`, `Review`, `Finding`, `Vote`) y los casos de
uso no dependen de Temporal, FastAPI, Postgres ni de los agentes; cada uno de esos es un
adaptador detrás de un puerto. Hoy existe un solo puerto implementado,
`ChangeRepository` (ver `change-ingestion` más abajo); `ReviewAgent`, `CodeHost` y
`EventPublisher` llegarán cuando los changes que los necesiten los introduzcan - no se
diseñan por adelantado. El detalle completo del producto final está en
[`docs/spec/duelo.md`](spec/duelo.md).

Este documento indexa las decisiones arquitectónicas registradas como ADR y las
capacidades activas (specs) a medida que se toman/implementan, en vez de repetir aquí lo
que ya está en el spec o en `openspec/specs/`.

## Decisiones registradas (ADR)

- [0001 - Temporal frente a alternativas](adr/0001-temporal-vs-alternativas.md): por qué
  Temporal orquesta las reviews en vez de una cola simple, DBOS, Hatchet, Inngest o
  Prefect.

## Capacidades activas (OpenSpec)

- [`service-health`](../openspec/specs/service-health/spec.md): liveness del proceso de
  la API (Fase 0).
- [`change-ingestion`](../openspec/specs/change-ingestion/spec.md): persistencia atómica
  e idempotente de un `Change` y su evento outbox, con límites de campo, recorte de
  metadatos y saneado de NUL (Fase 1).
- [`change-review`](../openspec/specs/change-review/spec.md): reviews en paralelo con
  `FakeAgent` mediante workflows de Temporal, tolerantes a fallos parciales, atómicas e
  idempotentes por `(change, agent, run)` (Fase 2, primer slice).
- [`commit-ingestion`](../openspec/specs/commit-ingestion/spec.md):
  `POST /ingest/commit` autenticado con token de ingesta; persiste el commit y arranca su
  review sin duplicar trabajo; `GET /ready` comprueba Postgres y Temporal (Fase 2, cierre).
  Contrato OpenAPI en [`openapi.json`](openapi.json).
- `change-queries` y `pr-ingestion` (change `round1-backend-api`): lecturas sin token
  (`GET /projects`, `GET /projects/{slug}/changes` con cursor, `GET /changes/{id}`,
  `GET /stats/agents`; ver la decisión sobre autenticación de lecturas en su `design.md`) y
  `POST /ingest/pr` con la misma identidad idempotente que los commits.
- `review-retry` y ampliaciones de `change-queries` y `service-health` (change
  `round2-backend-api`): el canal filtra por `status` de review y por texto (`q`); cada change
  expone `review_status` (`pending`/`running`/`partial_failed`/`failed`/`completed`, calculado
  sobre el `run` actual) y el detalle un `findings_summary`; `POST /changes/{id}/retry`
  (con token) lanza `run + 1` si la ejecución actual terminó con fallos, con id de workflow
  `-r{run}` desde el segundo run y `run` avanzado por compare-and-swap;
  `GET /health/dependencies` da estado y latencia de Postgres y Temporal.
- `change-events`, `review-raw-output` y ampliaciones de `change-queries`, `commit-ingestion` y
  `pr-ingestion` (change `round3-backend-api`): cada change expone `diff_summary` (archivos y
  líneas, calculado por `domain/diff.py` al ingerir y guardado en `changes.diff_summary`, de
  modo que el canal no carga el diff; la migración rellena los existentes);
  `GET /stats/agents?project=` filtra por proyecto; las respuestas de ingesta añaden `created`
  (se deduce comparando el id candidato con el que devuelve `ChangeRepository.add`);
  `GET /changes/{id}/events` lee el outbox con una lista blanca en la aplicación (sin el texto
  de los errores ni la salida cruda) y `GET /reviews/{id}/raw-output` da la salida cruda solo
  con `OPERATOR_TOKEN`, un secreto distinto del de ingesta (404 si no está configurado; ver los
  riesgos en su `design.md`).
- `api-cors`, `request-observability`, `rate-limiting` y `stale-reviews` (change
  `round4-backend-api`): CORS solo para los orígenes de `ALLOWED_ORIGINS` (sin `*` ni
  credenciales); `X-Request-ID` validado y access log JSON por petición con la plantilla de la
  ruta (nunca query, cuerpo ni tokens); límite de peticiones por IP en `POST /ingest/*` y
  `/changes/{id}/retry` (puerto `RateLimiter` con adaptador en memoria, 429 con `Retry-After`,
  `RATE_LIMIT_REQUESTS=0` lo desactiva; en memoria de un proceso, ver su `design.md`);
  `stale` en el listado y el detalle para changes `pending`/`running` más antiguos que
  `STALE_AFTER_SECONDS`. La migración `d4a8e1b5c602` reemplaza los índices del canal y la
  consulta del canal cuenta las reviews con un `LEFT JOIN LATERAL` (EXPLAIN con 60 000 changes:
  de ~58 ms a <1 ms).
- `change-review`, `review-retry` y `stale-reviews` (change `recover-review-runs`): si una
  activity `run_review` agota sus 3 intentos por un fallo de infraestructura, el workflow
  ejecuta la activity compensatoria `record_review_infrastructure_failure` y guarda una review
  `failed` con un mensaje fijo (nunca el texto de la excepción), idempotente por
  `(change, agent, run)`; así el change pasa a `failed`/`partial_failed` y es reintentable. Un
  error de configuración no reintentable (agente desconocido) sigue sin registrar nada. El cambio
  va bajo `workflow.patched("compensate-infra-failure")` para no romper ejecuciones en vuelo.
  `run_review` emite latidos cada 10 s mientras el agente trabaja (el `heartbeat_timeout` es de
  30 s). `changes.run_started_at` (migración `f6c4d8a2b915`, rellena desde `created_at`) lo fija la
  ingesta y lo refresca `advance_run`; `stale` se mide desde ahí, de modo que un reintento sobre
  un change antiguo no nace `stale`.
- `local-projects` (change `add-local-projects-backend`, apagado por defecto con
  `LOCAL_PROJECTS_ENABLED`): `POST /projects` da de alta un repo desde su carpeta (el slug sale de
  `origin`, `owner/repo`, o del nombre de la carpeta) e instala los hooks `post-commit` y
  `pre-push`; `DELETE /projects/{slug}` los quita y borra el proyecto con sus changes, reviews y
  eventos; `POST /projects/{slug}/sync-prs` ingesta las PRs abiertas con `gh` (y
  `PR_SYNC_INTERVAL_SECONDS` lo repite). Los puertos `GitRepository`, `HookInstaller`,
  `GithubPrSource` y `ProjectCatalog` viven en `application/ports.py`; los adaptadores usan un
  único ejecutor de subprocesos sin shell y con plazo (`adapters/subprocess_runner.py`). El hook
  es `duelo.entrypoints.hook` (solo biblioteca estándar): hace `fork`, envía en segundo plano y
  sale siempre con 0, y lee la URL y el token solo del fichero de credenciales cuya ruta lleva el
  bloque instalado (`--env-file`), nunca del entorno. La baja quita los hooks antes de borrar y
  responde 409 si no puede. `GET /projects` añade `path`, `hooks_installed` y `github`, y CORS permite
  `DELETE`. **Seguridad:** quien tenga `INGEST_TOKEN` hace que la API escriba hooks en repos del
  usuario; solo debe activarse con la API en la máquina del usuario y nunca en un contenedor ni
  expuesta (ver su `design.md`).
- `change-ingestion`, `local-projects` y `change-events` (change `harden-ingest-and-hooks`):
  `POST /ingest/commit` y `/ingest/pr` responden 413 si el cuerpo supera `MAX_INGEST_BODY_BYTES`
  (`entrypoints/api/body_limit.py`, ASGI puro: por `Content-Length` sin leer nada o contando el flujo;
  responde antes que el limitador y el token y es el más interno de los tres middlewares, así que
  lleva `X-Request-ID`); el truncado del diff a `MAX_DIFF_CHARS` sigue siendo el límite de negocio.
  El hook no sigue redirecciones (un 3xx es un fallo silencioso), de modo que el token no sale del
  host de la URL configurada. `GET /changes/{id}/events` ordena por `(created_at, id)`.
- `change-queries` / `service-health` (change `dynamic-agents-and-review-summaries`): cada
  elemento del canal lleva `reviews`, una lista ligera (`agent`, `status`, `score`, `duration_ms`,
  `run`) solo del `run` actual, obtenida con **una** consulta adicional por página y sin las
  columnas pesadas (`ReviewBrief` en `application/read_models.py`); `GET /health/dependencies`
  añade `agent_names` (de `AGENT_NAMES`) para que la UI no suponga «Claude y Codex». El frontend
  pide el detalle completo al abrir «Ver respuestas» y muestra del detalle solo el run actual, con
  los anteriores colapsados.

## Variables de entorno

| Variable | Por defecto | Qué hace |
| --- | --- | --- |
| `INGEST_TOKEN` | (obligatoria) | Secreto de ingesta y de `POST /changes/{id}/retry` |
| `OPERATOR_TOKEN` | sin configurar | Habilita `GET /reviews/{id}/raw-output` (distinto de `INGEST_TOKEN`, 16+ caracteres); sin él responde 404 |
| `DATABASE_URL`, `TEMPORAL_ADDRESS`, `AGENT_NAMES`, `MAX_DIFF_CHARS` | ver `config.py` | Conexiones y límites base |
| `MAX_INGEST_BODY_BYTES` | `1500000` | Tamaño máximo del cuerpo de `POST /ingest/commit` y `/ingest/pr` (413 si lo supera); protege la memoria y es independiente de `MAX_DIFF_CHARS` |
| `ALLOWED_ORIGINS` | vacía (sin CORS) | Orígenes `esquema://host[:puerto]` separados por comas, p. ej. `http://localhost:5173`; no admite `*` |
| `RATE_LIMIT_REQUESTS` | `300` | Peticiones por IP y ventana en ingesta y reintento; `0` lo desactiva |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Ventana deslizante del límite |
| `STALE_AFTER_SECONDS` | `1800` | A partir de cuándo un change sin terminar se marca `stale` |
| `LOCAL_PROJECTS_ENABLED` | `false` | Activa `POST /projects`, `DELETE /projects/{slug}` y `POST /projects/{slug}/sync-prs` (instalan hooks de git); apagado responden 404. Solo con la API en la máquina del usuario |
| `INGEST_URL` | `http://127.0.0.1:8000` | A dónde mandan los hooks los commits; cámbiala si arrancas la API en otro puerto |
| `HOOK_ENV_PATH` | `~/.config/duelo/hook.env` | Fichero (modo 0600) con `INGEST_URL` e `INGEST_TOKEN`; los hooks lo leen por la ruta que lleva su bloque y no hacen caso del entorno |
| `PR_SYNC_INTERVAL_SECONDS` | `0` | Cada cuántos segundos se sincronizan las PRs de los proyectos locales con `gh`; `0` = nunca |

## Calidad y tests

- [Estrategia de tests](testing.md): capas unit/integration, mutation testing, umbrales de
  cobertura y el mapa de cada tipo de test (cubierto / diferido con motivo).

## Regla de dependencias (backend)

```
domain  <-  application  <-  adapters / entrypoints / workflows
```

La única pieza que conoce a la vez `entrypoints`, `adapters` y `workflows` es la raíz de
composición (`duelo/composition.py` para la API y `duelo/worker.py` para el
worker de desarrollo); queda fuera de las capas a propósito.

Enforzada por `import-linter` (`backend/pyproject.toml`, sección
`[tool.importlinter]`), validado localmente con `just lint` y en CI.
