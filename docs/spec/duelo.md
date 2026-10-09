# Spec: Code Review Multi-Agente (Claude Code vs Codex)

Oct 6, 2026 · @Renzo

## Resumen y objetivos

Duelo es una web donde cada proyecto tiene su propio canal, al estilo Slack. Cada commit o PR que hago llega como un mensaje, y Claude Code y Codex responden debajo con su review, en paralelo. Voto qué review fue más útil (a ciegas, sin saber de qué agente es) y el dashboard muestra quién revisa mejor. En cada canal también puedo preguntar a `@claude` o `@codex` sobre el proyecto.

Qué demuestra en el portafolio: arquitectura limpia (hexagonal), workflows durables con Temporal, tiempo real fiable, contratos tipados entre back y front y, sobre todo, **evaluación rigurosa de agentes con datos propios**.

**Alcance del MVP**

- Proyectos como canales, con ajustes por proyecto: comentar en PRs, ramas a revisar y rutas ignoradas.
- Ingesta de commits locales (hook) y PRs (webhook), sin duplicados.
- Review de Claude Code y Codex en paralelo, con reintentos, timeouts y límite de concurrencia.
- Respuestas en vivo en el canal (SSE que se reengancha sin perder eventos).
- Preguntas a los agentes desde el chat del canal.
- Voto ciego y estadísticas por agente y por versión de prompt.
- Modo demo público con datos de ejemplo para el portafolio.

**Fuera de alcance (por ahora)**

- Multiusuario y login real: es una herramienta personal que corre en local.
- Aplicar automáticamente los cambios sugeridos.
- App de escritorio: el producto es solo web.
- Más agentes (Gemini CLI, etc.): la arquitectura lo permite con un adaptador nuevo.

## Qué cambia en la v2

| Antes | Ahora | Por qué |
| --- | --- | --- |
| Feed único | Un canal por proyecto, con chat para preguntar a los agentes | Mejor organización; los agentes aportan también fuera de la review |
| Código organizado por tipo de archivo | Arquitectura hexagonal: dominio, casos de uso y adaptadores | El dominio no depende de Temporal, FastAPI ni de los CLIs, y se testea aislado |
| Un worker para todo | Dos task queues: `agents` (en tu máquina) y `platform` (en Docker) | Solo lo que necesita los CLIs logueados corre fuera de Docker; concurrencia limitada para no agotar el plan |
| Un workflow por commit, también en PRs | `PullRequestWorkflow` de larga duración con señales y debounce | Diez pushes seguidos no lanzan diez reviews; la review obsoleta se cancela |
| `NOTIFY` directo desde las activities | Outbox: tabla `events` escrita en la misma transacción | Ningún evento se pierde y el front recupera lo perdido al reconectar |
| Cliente del front escrito a mano | Cliente TypeScript generado desde el OpenAPI | Back y front no se desincronizan; CI lo comprueba |
| Votos con el agente visible | Voto ciego + `prompt_version` y versión del agente en cada review | Evaluación sin sesgo y comparable entre versiones |
| Solo filtrar `.env` | Escaneo de secretos (gitleaks) antes de enviar el diff + token en la ingesta | Ningún secreto sale hacia los agentes; nadie más puede inyectar commits |
| Sin estrategia de tests | Pirámide de tests, Temporal time-skipping y un agente falso para e2e | Tests rápidos y deterministas sin gastar el plan |
| Solo local | Modo demo desplegado con datos de ejemplo | Un reclutador lo ve sin instalar nada |

## ¿Tiene sentido Temporal?

Sí. Cada review es una tarea larga (30 s a 5 min), con dos agentes que pueden fallar, colgarse o toparse con el límite de uso del plan. Ese es exactamente el problema que resuelve Temporal.

| Necesidad del proyecto | Sin Temporal | Con Temporal |
| --- | --- | --- |
| Ejecutar Claude y Codex en paralelo | `asyncio` a mano | Dos activities lanzadas a la vez |
| Reintentar si un CLI falla o hay rate limit | Lógica propia de reintentos | `RetryPolicy` declarativa con backoff |
| Matar una review colgada | Timeouts manuales | `start_to_close_timeout` por activity |
| No perder trabajo si se reinicia el backend | Se pierde | El workflow continúa donde iba |
| Ver qué pasó en cada review | Logs sueltos | Historial completo en la Temporal Web UI |
| Evitar revisar dos veces el mismo commit | Control propio | Workflow ID = SHA del commit |

**Contras:** un servicio más que levantar (se resuelve con `temporal server start-dev` o Docker Compose) y curva de aprendizaje inicial.

**Alternativa más simple:** FastAPI + una cola (ARQ o Celery con Redis). Funciona, pero tendrías que reimplementar reintentos, timeouts y visibilidad. Para portafolio, Temporal suma más: es tecnología que usan empresas reales y demuestra criterio de arquitectura.

## Principios de arquitectura

1. **Hexagonal (puertos y adaptadores).** El dominio (`Change`, `Review`, `Finding`, `Vote`) y los casos de uso no importan nada de infraestructura. Temporal, FastAPI, Postgres, GitHub y cada agente son adaptadores que implementan un puerto: `ReviewAgent`, `CodeHost`, `ChangeRepository`, `EventPublisher`.
2. **Monolito modular con tres entradas.** Un solo paquete Python con tres procesos: API, worker `platform` y worker `agents`. Sin microservicios: a este tamaño solo añaden complejidad.
3. **IDs, no datos, por Temporal.** Workflows y activities reciben IDs; los diffs viven en Postgres. El historial de Temporal queda pequeño (cada payload tiene límite de 2 MB) y legible.
4. **Activities idempotentes.** Toda escritura es un upsert con clave natural (`change_id`, `agent`, `run`); reintentar nunca duplica.
5. **Outbox para eventos.** Cada cambio de estado escribe su fila en `events` en la misma transacción y un trigger hace `NOTIFY`. El front se reengancha con `Last-Event-ID`.
6. **Contrato primero.** Los modelos Pydantic son la fuente de verdad; el OpenAPI genera el cliente TypeScript.
7. **Configuración 12-factor.** Todo por variables de entorno con `pydantic-settings`; ningún secreto en el repo.
8. **Decisiones documentadas.** Cada decisión importante tiene su ADR en `docs/adr/`, por ejemplo "0001 – Temporal frente a DBOS".

## Stack tecnológico

Python en el backend porque es donde ya trabajas y el SDK de Temporal para Python es maduro; TypeScript en el front porque es el estándar.

| Capa | Elección | Por qué |
| --- | --- | --- |
| Lenguaje backend | Python 3.12 + `uv` | Gestión de dependencias rápida y moderna |
| API | FastAPI | Async, tipado con Pydantic, docs automáticas en `/docs` |
| Workflows | Temporal (`temporalio` SDK) | Reintentos, timeouts, paralelismo y visibilidad |
| Base de datos | PostgreSQL + SQLAlchemy 2.0 async + Alembic | Necesario para outbox, LISTEN/NOTIFY y jsonb; SQLAlchemy separa el modelo de BD del dominio (SQLModel los mezcla) |
| Tiempo real | Server-Sent Events (`sse-starlette`) + Postgres `LISTEN/NOTIFY` | Unidireccional, con outbox y reconexión nativa vía Last-Event-ID |
| Frontend | React 19 + Vite + TypeScript strict | Solo web; estándar del sector, arranque rápido |
| UI | Tailwind CSS + shadcn/ui | Estética tipo GitHub; color secundario con variables CSS |
| Datos en el front | TanStack Query + Router | Caché de datos y rutas tipadas |
| Diff y reviews | `react-markdown` + Monaco diff editor | Diff lado a lado como en GitHub; reviews en Markdown |
| GitHub | `gh` CLI + webhooks (`gh webhook forward` en local) | API de GitHub con githubkit (cliente tipado); gh solo para reenviar webhooks en local |
| Agentes | `Claude Agent SDK` y `codex exec` | SDK tipado para Claude; CLI de Codex. Ver integración |
| Infra local | Docker Compose | Postgres, Temporal, Temporal UI, API y worker platform, con perfiles |
| Calidad | Ruff, mypy strict, Biome, pre-commit | Lint, tipos y formato en todo el repo; Conventional Commits |
| CI | GitHub Actions | Lint, tipos, tests y deriva del OpenAPI en cada PR; Renovate para dependencias |
| Cliente API | openapi-typescript + openapi-fetch | Tipos generados desde el backend: cero desincronización |
| Seguridad | gitleaks | Escanea el diff antes de enviarlo a los agentes |
| Observabilidad | OpenTelemetry + Langfuse + structlog | Trazas de punta a punta, métricas de agentes y logs JSON |
| Tests | pytest, testcontainers, Temporal time-skipping, Vitest, MSW, Playwright | Pirámide completa sin gastar plan |
| Tareas | just | Un comando por tarea: just dev, just test, just gen-client |

## Observabilidad y evaluación

Tres niveles: OpenTelemetry sigue cada petición de punta a punta, Langfuse mide a los agentes y promptfoo da un benchmark reproducible.

| Herramienta | Para qué | Cómo se integra |
| --- | --- | --- |
| OpenTelemetry | Una sola traza desde el webhook hasta la review guardada | Instrumentación de FastAPI y SQLAlchemy + interceptor de Temporal |
| structlog | Logs JSON con `trace_id`, `change_id` y `workflow_id` | Configurado igual en los tres procesos |
| Langfuse (Cloud) | Traza por review: prompt, salida, duración y errores | `@observe` en el adaptador de cada agente; `langfuse_trace_id` en la review |
| Langfuse scores | Votos y nota del agente como métricas | Cada voto se envía como score a su traza |
| promptfoo | Benchmark offline: 25 diffs con un bug conocido cada uno | Un proveedor por agente; asserts sobre los `findings` |

**Buenas prácticas de evaluación**

- **Voto ciego:** el front muestra "Agente A" y "Agente B" en orden aleatorio hasta que votas; así el nombre no sesga el voto.
- **Versionado:** cada review guarda `prompt_version`, `agent_version` y `model`. Las estadísticas se filtran por versión para comparar cambios de prompt de forma justa.
- **Prompts como código:** viven en `prompts/review/v{n}.md`; cambiar el prompt es una PR que también revisan los agentes.
- **Métricas del benchmark:** % de bugs detectados, falsos positivos por review, nota media y duración. Se lanza a mano o con un Temporal Schedule semanal, nunca en cada CI, porque gasta plan.

## Arquitectura

Tres procesos propios. La API y el worker `platform` corren en Docker junto a Postgres y Temporal; el worker `agents` corre en tu máquina, donde Claude Code y Codex están logueados. No se llaman entre sí: se coordinan a través de Temporal (el trabajo) y de Postgres (el estado y los eventos).

&#91;embedded content: arquitectura · 7 componentes\]

**Flujo de un commit, de principio a fin**

1. Haces `git commit`; el hook envía el diff a `POST /ingest/commit` con el token del proyecto.
2. La API valida, guarda el `change` y su evento `change.created` en la misma transacción, y arranca `ReviewCommitWorkflow` con ID `commit-{project}-{sha}`.
3. El worker `platform` prepara el contexto y escanea secretos; el worker `agents` ejecuta Claude Code y Codex en paralelo, como máximo dos a la vez.
4. Cada resultado se guarda junto a su evento en `events`, y un trigger hace `NOTIFY`.
5. La API reenvía el evento por SSE al canal del proyecto y la respuesta aparece en vivo.
6. En PRs, si el proyecto lo tiene activado, `platform` publica las reviews como comentario.

## Workflows de Temporal

Tres workflows padre comparten un workflow hijo, `ReviewChangeWorkflow`, que hace la review en sí.

| Workflow | ID | Cuándo se inicia | Qué hace |
| --- | --- | --- | --- |
| `ReviewCommitWorkflow` | `commit-{project}-{sha}` | Hook post-commit | Lanza el hijo una vez |
| `PullRequestWorkflow` | `pr-{project}-{número}` | Webhook, con signal-with-start en cada push | Vive mientras la PR está abierta: espera 60 s sin pushes (debounce), cancela la review obsoleta y revisa el último SHA |
| `AnswerQuestionWorkflow` | `ask-{message_id}` | Mensaje con `@claude` o `@codex` en el chat | Monta el contexto (último diff y reviews del canal) y responde en el hilo |

El hijo, `ReviewChangeWorkflow`:

&#91;embedded content: ReviewChangeWorkflow · 6 pasos, 1 decisión\]

| Activity | Queue | Timeout | Reintentos | Qué hace |
| --- | --- | --- | --- | --- |
| `prepare_context` | platform | 1 min | 3 | Carga el diff, aplica rutas ignoradas y escanea secretos con gitleaks |
| `run_review` | agents | 10 min, heartbeat 30 s | 3, backoff desde 30 s | Ejecuta el agente, valida el JSON y guarda review + evento |
| `post_comments` | platform | 1 min | 5 | Comenta en la PR vía githubkit |
| `finish_change` | platform | 30 s | 5 | Cierra el change y marca como `failed` lo que no terminó |

El worker `agents` arranca con `max_concurrent_activities=2` para no agotar el plan. Los errores no recuperables (JSON inválido tras 2 intentos, secreto detectado) se lanzan como `ApplicationError(non_retryable=True)`: reintentarlos solo gastaría plan.

```python
@workflow.defn
class ReviewChangeWorkflow:
    @workflow.run
    async def run(self, ref: ChangeRef) -> None:
        ctx = await workflow.execute_activity(
            prepare_context, ref, task_queue="platform",
            start_to_close_timeout=timedelta(minutes=1), retry_policy=RETRY)

        # Agentes activos del proyecto, en paralelo; un fallo no cancela al otro
        await asyncio.gather(*(
            workflow.execute_activity(
                run_review, ReviewRequest(ctx.change_id, agent, ctx.run),
                task_queue="agents",
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(seconds=30),
                retry_policy=RETRY)
            for agent in ctx.agents
        ), return_exceptions=True)

        if ctx.is_pr and ctx.post_to_github:
            await workflow.execute_activity(
                post_comments, ctx.change_id, task_queue="platform",
                start_to_close_timeout=timedelta(minutes=1), retry_policy=RETRY)

        await workflow.execute_activity(
            finish_change, ctx.change_id, task_queue="platform",
            start_to_close_timeout=timedelta(seconds=30))
```

**`PullRequestWorkflow`: debounce y cancelación**

```python
@workflow.defn
class PullRequestWorkflow:
    def __init__(self) -> None:
        self._latest_sha: str | None = None
        self._closed = False

    @workflow.signal
    def new_push(self, sha: str) -> None:
        self._latest_sha = sha

    @workflow.signal
    def closed(self) -> None:
        self._closed = True

    @workflow.run
    async def run(self, pr: PullRequestRef) -> None:
        reviewed: str | None = None
        while not self._closed:
            await workflow.wait_condition(
                lambda: self._closed or self._latest_sha != reviewed)
            if self._closed:
                break
            sha = self._latest_sha
            try:  # debounce: 60 s sin pushes nuevos
                await workflow.wait_condition(
                    lambda: self._latest_sha != sha, timeout=timedelta(seconds=60))
                continue
            except asyncio.TimeoutError:
                pass

            child = await workflow.start_child_workflow(
                ReviewChangeWorkflow.run, ChangeRef(pr.project_id, sha),
                id=f"review-{pr.project_id}-{sha}")
            new_push = asyncio.ensure_future(workflow.wait_condition(
                lambda: self._closed or self._latest_sha != sha))
            await workflow.wait([child, new_push], return_when=asyncio.FIRST_COMPLETED)
            if child.done():
                reviewed = sha
            else:
                child.cancel()  # la review quedó obsoleta

            if workflow.info().is_continue_as_new_suggested():
                workflow.continue_as_new(pr)
```

**Buenas prácticas de Temporal aplicadas**

- Un solo argumento dataclass por workflow y activity (`ChangeRef`, `ReviewRequest`): se pueden añadir campos sin romper los workflows en curso.
- Código de workflow determinista: nada de I/O, `datetime.now()` ni `random`; todo eso va en activities.
- `workflow.patched()` para cambiar la lógica sin romper workflows que ya están en marcha.
- `continue_as_new` en `PullRequestWorkflow` para que el historial no crezca sin límite en PRs largas.
- `POST /changes/{id}/rerun` incrementa `run` y lanza el hijo con ID `review-{project}-{sha}-r{run}`.

## Modelo de datos

Siete tablas. Un `project` es un canal; un `change` es cualquier cosa revisable (commit o PR); cada change tiene una `review` por agente y ejecución; el chat vive en `messages` y `events` es el outbox.

| Tabla | Campos clave | Notas |
| --- | --- | --- |
| `projects` | id, slug, full\_name, local\_path, settings (jsonb), ingest\_token\_hash | `settings`: comentar en PRs, ramas a revisar, rutas ignoradas, agentes activos |
| `changes` | id, project\_id, kind (`commit`/`pr`), ref, head\_sha, title, author, url, diff, diff\_truncated, status, run, created\_at | Única por (`project_id`, `kind`, `head_sha`) |
| `reviews` | id, change\_id, agent, run, status, summary, score, findings (jsonb), raw\_output, prompt\_version, agent\_version, model, duration\_ms, langfuse\_trace\_id, error | Única por (`change_id`, `agent`, `run`): la base de la idempotencia |
| `votes` | id, review\_id, value (+1/−1), note, blind, created\_at | Un voto por review; `blind` indica si se votó sin ver el agente |
| `messages` | id, project\_id, change\_id (nullable), parent\_id, author (`user`/`claude`/`codex`), body, status, created\_at | Chat del canal; una mención lanza `AnswerQuestionWorkflow` |
| `events` | id (bigserial), project\_id, type, payload (jsonb), created\_at | Outbox, escrito en la misma transacción; su `id` es el `Last-Event-ID` del SSE |
| `user_settings` | key, value (jsonb) | Color secundario, voto ciego y demás preferencias |

Índices: `changes (project_id, created_at desc)` para cargar el canal, `reviews (agent, prompt_version)` para las estadísticas y la PK de `events` para el reenganche. Los eventos de más de 30 días se purgan con un Temporal Schedule.

## API del backend

REST + un stream SSE. Todos los modelos son Pydantic y el OpenAPI resultante genera el cliente del front.

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET / POST | `/projects` | Lista y crea proyectos (canales) |
| PATCH | `/projects/{slug}` | Cambia los ajustes del proyecto |
| GET | `/projects/{slug}/changes?kind=&cursor=` | Mensajes del canal, paginados por cursor |
| GET | `/changes/{id}` | Detalle: diff + reviews de cada agente |
| POST | `/changes/{id}/rerun` | Nueva ejecución de la review (`run` + 1) |
| POST | `/reviews/{id}/votes` | Voto `+1` / `-1`, ciego o no, con nota opcional |
| GET / POST | `/projects/{slug}/messages` | Leer y escribir en el chat del canal |
| GET | `/stats?project=&prompt_version=` | Métricas por agente, filtrables por proyecto y versión de prompt |
| GET / PUT | `/settings` | Preferencias de la web: color secundario, voto ciego |
| POST | `/ingest/commit` | Desde el hook, con cabecera `X-Ingest-Token` |
| POST | `/webhooks/github` | Eventos `pull_request`, con firma HMAC obligatoria |
| GET | `/events?project=` | Stream SSE; acepta `Last-Event-ID` |
| GET | `/health`, `/ready` | Vida del proceso y estado de Postgres y Temporal |

**Eventos SSE:** `change.created`, `review.started`, `review.completed`, `review.failed`, `change.done` y `message.created`. Cada uno lleva `id` (del outbox), `type` y un payload tipado que también aparece en el OpenAPI.

**Convenciones:** errores con Problem Details (RFC 9457), paginación por cursor, `Idempotency-Key` en la ingesta y la API escuchando solo en `127.0.0.1`, salvo en modo demo.

## Frontend

Layout tipo Slack con tema negro único (ver ADR 0002): barra lateral con un canal por proyecto y una sección General. La demo interactiva está en el canvas "Duelo · Demo del front".

| Pantalla | Ruta | Contenido |
| --- | --- | --- |
| Canal | `/p/:slug` | Mensajes de commits y PRs; bajo cada uno, "Ver respuestas" despliega las reviews de Claude y Codex. Filtro Todo / PRs / Commits y caja de chat para preguntar con `@claude` o `@codex` |
| Detalle | `/p/:slug/changes/:id` | Diff en Monaco (lado a lado) y las dos reviews; votos, reintentar y enlace a Langfuse |
| Estadísticas | `/stats` | Por agente y versión de prompt: % útiles, nota media, duración, fallos y benchmark |
| Ajustes | `/settings` | Color secundario, voto ciego, proyectos vigilados y agentes activos |

**Organización del código:** por funcionalidad (`features/channel`, `features/review`, `features/stats`, `features/settings`), no por tipo de archivo. Cada feature agrupa sus componentes, hooks y queries.

**Tiempo real:** `useEventStream(slug)` abre `EventSource('/events?project=slug')` y, con cada evento, actualiza la caché de TanStack Query con `setQueryData`, sin refetch. Si la conexión se corta, el navegador reconecta solo y el servidor reenvía lo perdido gracias a `Last-Event-ID`.

**Tema:** negro único con tokens CSS (`--bg`, `--surface`, `--border`, `--fg-muted`, `--accent`…) y acento monocromo; sin modo claro. El color secundario configurable queda diferido (ADR 0002). Estados de carga de IA con `border-beam` y `thinking-orbs`, con fallback bajo `prefers-reduced-motion`.

**Accesibilidad:** navegación completa con teclado, `aria-expanded` en los hilos desplegables y contraste AA comprobado con el color elegido; si no llega, el tono se oscurece automáticamente.

## Integración con Claude Code y Codex

Ambos agentes reciben el mismo prompt y devuelven el mismo JSON, para poder compararlos de forma justa.

**Comandos (headless, solo lectura)**

| Agente | Comando | Notas |
| --- | --- | --- |
| Claude Code | `claude -p "<prompt>" --output-format json --disallowedTools "Edit,Write,Bash"` | La respuesta viene en el campo `result` del JSON |
| Codex | `codex exec --sandbox read-only "<prompt>"` | Si tu versión soporta `--output-schema`, úsalo para forzar el JSON |

**Recomendado para Claude: Claude Agent SDK.** En lugar de lanzar `claude -p`, la activity usa el SDK de Python: mensajes tipados, herramientas limitadas y errores claros. Comprueba en su documentación si admite tu login de suscripción; si exige API key, el CLI queda como respaldo.

```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

async def review_with_claude(prompt: str, repo_path: str) -> str:
    options = ClaudeAgentOptions(
        cwd=repo_path,
        allowed_tools=["Read", "Grep", "Glob"],  # solo lectura
        max_turns=10,
    )
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, ResultMessage):
            return msg.result
    raise RuntimeError("Claude no devolvió resultado")
```

Para Codex se mantiene `codex exec` desde Python: el Codex SDK es TypeScript (ver Alternativas consideradas).

Ambos se ejecutan con `cwd` = ruta local del repo, para que puedan leer archivos y entender el contexto del cambio, no solo el diff. Revisa con `--help` las flags exactas de tu versión antes de empezar, porque cambian entre versiones.

**Prompt común (versionado en prompts/review/v1.md)**

```text
Eres un revisor de código senior. Revisa el siguiente cambio ({kind}: {title}).
Puedes leer archivos del repo para entender el contexto, pero NO modifiques nada.
Responde SOLO con un JSON válido con esta forma:
{"summary": "...", "score": 1-10, "findings": [
  {"severity": "bug|risk|improvement|nit", "file": "...", "line": 0, "message": "..."}
]}
Responde en español.

DIFF:
{diff}
```

**Parseo:** extraer el JSON, validarlo con un modelo Pydantic `ReviewResult` y, si no valida, lanzar un error para que Temporal reintente (máximo 2 veces). La salida cruda se guarda siempre en `raw_output`.

**El puerto `ReviewAgent`.** Los casos de uso solo conocen esta interfaz; Claude, Codex y el agente falso de los tests son adaptadores intercambiables. El prompt se envuelve marcando el diff como datos, nunca como instrucciones, para reducir el riesgo de prompt injection desde el código revisado.

```python
class ReviewAgent(Protocol):
    name: str

    async def review(self, ctx: ReviewContext) -> ReviewResult: ...
    async def answer(self, ctx: QuestionContext) -> str: ...
    async def version(self) -> str: ...   # se guarda en reviews.agent_version

AGENTS: dict[str, ReviewAgent] = {
    "claude": ClaudeAgent(), "codex": CodexAgent(), "fake": FakeAgent(),
}
```

**Suscripción vs API**

- Claude Code: `claude login` con tu cuenta Pro/Max y **sin** `ANTHROPIC_API_KEY` en el entorno del worker. Consume tu límite de uso del plan, no se factura por token.
- Codex: `codex login` con tu cuenta de ChatGPT, misma idea.
- Consecuencia: el worker que ejecuta estas activities corre en **tu máquina**, donde están los CLIs logueados. Es uso personal; para un producto con otros usuarios habría que pasar a API keys.

## Ingesta de commits y PRs

Dos entradas principales y una de respaldo. Todas acaban llamando a la misma función `start_review(change)`, que arranca el workflow con ID determinista para no duplicar.

**1. Commits locales: hook `post-commit`**

Un script `scripts/install-hook.sh` instala este hook en cada repo que quieras vigilar:

```bash
#!/bin/sh
# .git/hooks/post-commit
REPO=$(git remote get-url origin 2>/dev/null || basename "$PWD")
jq -n --arg repo "$REPO" --arg sha "$(git rev-parse HEAD)" \
      --arg title "$(git log -1 --pretty=%s)" --arg author "$(git log -1 --pretty=%an)" \
      --arg diff "$(git show HEAD --format= | head -c 20000)" \
      '{repo:$repo, sha:$sha, title:$title, author:$author, diff:$diff}' \
  | curl -s -X POST http://localhost:8000/ingest/commit \
      -H 'Content-Type: application/json' -H "X-Ingest-Token: $REVIEW_ARENA_TOKEN" --data-binary @- >/dev/null 2>&1 &
```

El `&` final lo ejecuta en segundo plano: el commit nunca se bloquea, aunque el backend esté apagado.

**2. PRs: webhook de GitHub**

- Evento `pull_request` con acciones `opened` y `synchronize` (nuevo push), que llegan como señales a PullRequestWorkflow, y closed, que lo termina.
- Validar la cabecera `X-Hub-Signature-256` con el secreto del webhook.
- En local, sin exponer puertos: `gh webhook forward --repo=usuario/repo --events=pull_request --url=http://localhost:8000/webhooks/github`.
- El diff se obtiene en una activity con `githubkit dentro de prepare_context`.

**3. Respaldo: polling (opcional)**

Un Temporal Schedule cada 5 minutos ejecuta `gh search prs --author=@me` y arranca reviews de las PRs que falten. Cubre los eventos perdidos mientras el backend estaba apagado.

## Estructura del repositorio

Monorepo con arquitectura hexagonal en el backend y organización por funcionalidad en el front. Regla de dependencias: `domain` ← `application` ← `adapters` / `entrypoints` / `workflows`; `import-linter` la hace cumplir en CI.

```text
duelo/
├── justfile                    # just dev · just test · just gen-client
├── docker-compose.yml          # perfiles: infra, app
├── .pre-commit-config.yaml     # ruff, mypy, biome, gitleaks
├── docs/
│   ├── adr/                    # 0001-temporal.md, 0002-outbox.md…
│   └── architecture.md
├── prompts/review/v1.md        # prompts versionados
├── scripts/install-hook.sh
├── backend/
│   ├── pyproject.toml          # uv
│   ├── alembic/
│   ├── src/duelo/
│   │   ├── domain/             # entidades y reglas puras: Change, Review, Finding, Vote
│   │   ├── application/        # casos de uso + puertos
│   │   │   ├── ports.py        # ReviewAgent, CodeHost, ChangeRepository, EventPublisher
│   │   │   ├── ingest_change.py
│   │   │   ├── record_review.py
│   │   │   └── cast_vote.py
│   │   ├── adapters/
│   │   │   ├── agents/         # claude.py, codex.py, fake.py
│   │   │   ├── github/         # githubkit + verificación de webhooks
│   │   │   ├── persistence/    # SQLAlchemy: tablas, repositorios, outbox
│   │   │   └── security/       # gitleaks
│   │   ├── workflows/          # workflows + activities finas que llaman a casos de uso
│   │   ├── entrypoints/
│   │   │   ├── api/            # FastAPI: routers, schemas, SSE
│   │   │   ├── worker_platform.py
│   │   │   └── worker_agents.py
│   │   └── config.py           # pydantic-settings
│   └── tests/                  # unit/, integration/, workflows/
├── frontend/
│   ├── package.json            # pnpm
│   └── src/
│       ├── app/                # router, providers, tema
│       ├── features/           # channel/, review/, stats/, settings/
│       ├── shared/             # ui/ (shadcn), lib/, hooks/useEventStream.ts
│       └── api/schema.d.ts     # generado desde el OpenAPI
├── e2e/                        # Playwright con FakeAgent
└── benchmark/                  # promptfoo: casos con bugs conocidos
```

Nombre: **Duelo** (dos agentes compitiendo por dar la mejor review).

## Calidad y testing

| Nivel | Qué se prueba | Herramienta |
| --- | --- | --- |
| Unitario | Dominio y casos de uso con puertos falsos | pytest |
| Integración | Repositorios, outbox y API contra un Postgres real | pytest + testcontainers + httpx |
| Workflows | Debounce, cancelación, reintentos y fallos parciales, sin esperar tiempo real | `WorkflowEnvironment.start_time_skipping()` + activities simuladas |
| Replay | Que un cambio de código no rompa workflows en curso | `Replayer` de Temporal con historiales guardados |
| Contrato | Que el cliente generado coincida con el OpenAPI actual | `just gen-client` + `git diff --exit-code` en CI |
| Front | Componentes y hooks con la API simulada | Vitest + Testing Library + MSW |
| E2E | Commit → review → voto en el navegador | Playwright con `FakeAgent`, sin gastar plan |
| Calidad de agentes | Bugs detectados en casos conocidos | promptfoo, fuera de CI |

**CI en cada PR:** lint y formato → tipos (mypy strict y `tsc`) → import-linter → tests unitarios y de workflows → integración con testcontainers → contrato OpenAPI → build del front → e2e con Playwright. Cobertura mínima del 80 % en `domain` y `application`.

**Hábitos:** Conventional Commits, PRs pequeñas, un ADR por decisión importante y `pre-commit` con gitleaks para que ningún secreto llegue al repo.

## Despliegue y modo demo

El sistema real corre en local, porque el worker `agents` necesita tus CLIs logueados. Para el portafolio hay un **modo demo** público:

- Con `DEMO_MODE=true` la API solo lee, los votos se guardan en el navegador y un seed carga proyectos, commits y reviews reales anonimizadas.
- Un botón "Simular commit" lanza el workflow con `FakeAgent`, que reproduce respuestas grabadas con retardos realistas: se ve el flujo en vivo sin gastar plan.
- Front en Vercel; API, Postgres y Temporal en un VPS pequeño con el mismo Docker Compose.
- README con GIF, diagrama de arquitectura, enlace a la demo y resultados del benchmark.

## Plan de implementación

Siete fases; cada una termina con algo que funciona, tiene tests y se puede enseñar. La calidad va desde el día 1, no al final.

1. **Fase 0 – Base y calidad.** Monorepo, `just`, Docker Compose, pre-commit, CI y ADR 0001; FastAPI con `/health`.
   - [ ] Hecho cuando: `just dev` levanta todo y una PR vacía pasa la CI en verde.
2. **Fase 1 – Dominio y persistencia.** Entidades, casos de uso, repositorios SQLAlchemy, outbox y migraciones.
   - [ ] Hecho cuando: `ingest_change` guarda el change y su evento en una transacción, probado con testcontainers.
3. **Fase 2 – Workflows con agente falso.** `ReviewChangeWorkflow`, `ReviewCommitWorkflow`, las dos task queues y tests con time-skipping.
   - [ ] Hecho cuando: un commit produce dos reviews de `FakeAgent` y el test de fallo parcial pasa.
4. **Fase 3 – Agentes reales.** Adaptadores de Claude y Codex, gitleaks, prompt v1 y Langfuse.
   - [ ] Hecho cuando: un commit real produce dos reviews válidas, cada una con su traza.
5. **Fase 4 – Front en vivo.** Canales, hilos desplegables, SSE con reenganche, cliente generado y tema configurable.
   - [ ] Hecho cuando: el commit aparece en vivo, y cortar y recuperar la red no pierde eventos.
6. **Fase 5 – PRs y chat.** Webhook, `PullRequestWorkflow` con debounce, comentarios en GitHub y `AnswerQuestionWorkflow`.
   - [ ] Hecho cuando: tres pushes seguidos generan una sola review y `@claude` responde en el hilo.
7. **Fase 6 – Evaluación y demo.** Voto ciego, estadísticas por versión de prompt, benchmark, modo demo desplegado y README.
   - [ ] Hecho cuando: la demo es pública y hay más de 20 reviews votadas con conclusiones en el README.

La fase 6 es la que más pesa en el portafolio: "Claude vs Codex en mis propios commits, con voto ciego y benchmark" es lo que se recuerda en una entrevista.

## Riesgos, seguridad y decisiones abiertas

| Riesgo | Mitigación |
| --- | --- |
| Límite de uso del plan | Concurrencia 2 en `agents`, debounce en PRs, backoff largo y errores no reintentables |
| Diffs enormes | Recorte con `diff_truncated` y rutas ignoradas (lockfiles, generados); el agente lee archivos del repo si necesita contexto |
| JSON inválido | Validación Pydantic, 2 intentos y `raw_output` siempre guardado |
| Un agente modifica el repo | Solo lectura: `allowed_tools` en Claude, `--sandbox read-only` en Codex |
| Secretos en el diff | gitleaks en `prepare_context`: si detecta algo, no se envía y la review queda bloqueada con aviso |
| Ingesta o webhooks falsificados | Token por proyecto guardado como hash, firma HMAC y API solo en localhost |
| Prompt injection desde el código revisado | Diff delimitado como datos en el prompt; los agentes no tienen herramientas de escritura |
| Cambios en CLIs y SDKs | Cada agente tras su adaptador, versiones fijadas y `agent_version` guardado |
| Workflows en curso al desplegar código nuevo | `workflow.patched()` y tests de replay |

**Decisiones abiertas**

- [ ] ¿Revisar también los commits en `main` o solo en ramas de trabajo? Es configurable por proyecto; falta el valor por defecto.
- [ ] ¿Voto ciego activado por defecto?
- [ ] ¿Añadir Gemini CLI como tercer agente después de la fase 6?

## Alternativas consideradas

Temporal se mantiene. El resto queda registrado para justificar las decisiones en entrevistas.

| Opción | Decisión | Motivo |
| --- | --- | --- |
| DBOS | Plan B | Workflows durables como librería sobre Postgres, si Temporal pesa demasiado |
| Hatchet | Descartada | Más ligero, pero suma menos en el CV que Temporal |
| Inngest / Prefect | Descartadas | Orientados a serverless y a pipelines de datos |
| Supabase Realtime | Opcional | Sustituye LISTEN/NOTIFY + SSE con menos código, pero oculta cómo funciona |
| Codex SDK (TypeScript) | Opcional | Exige un worker TS de Temporal en otra task queue; buen extra políglota |
| Tauri | Descartada | El producto es solo web |
