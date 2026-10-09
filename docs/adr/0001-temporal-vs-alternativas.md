# 0001. Temporal frente a alternativas para orquestar las reviews

- Estado: Aceptada
- Fecha: 2026-10-08

Convención de numeración: `docs/adr/{número incremental de 4 dígitos}-{slug}.md`, un ADR
por decisión arquitectónica significativa.

## Contexto

Cada review es una tarea larga (30 s a 5 min) que ejecuta dos agentes (Claude Code y
Codex) en paralelo, cualquiera de los cuales puede fallar, colgarse o toparse con el
límite de uso del plan de suscripción. El sistema necesita:

- Ejecutar ambos agentes en paralelo sin bloquear al otro si uno falla.
- Reintentar con backoff cuando un CLI falla o hay rate limit.
- Matar una review colgada sin matar el proceso completo.
- No perder trabajo en curso si el backend se reinicia.
- Ver qué pasó en cada review (historial, no solo logs sueltos).
- No revisar dos veces el mismo commit, incluso con reintentos o reinicios.
- En las PRs, no lanzar una review por cada uno de varios pushes seguidos en segundos.

## Decisión

Usar [Temporal](https://temporal.io/) (SDK `temporalio` para Python) como motor de
workflows durables, con `ReviewChangeWorkflow` como hijo compartido por
`ReviewCommitWorkflow`, `PullRequestWorkflow` (con señales y debounce) y
`AnswerQuestionWorkflow`. Detalle en `docs/spec/duelo.md` (sección "Workflows de
Temporal").

## Alternativas consideradas

| Opción | Decisión | Motivo |
| --- | --- | --- |
| FastAPI + cola (ARQ/Celery + Redis) | Descartada para este proyecto | Resuelve la ejecución en background, pero reintentos, timeouts y visibilidad del historial habría que reimplementarlos a mano |
| DBOS | Plan B | Workflows durables como librería sobre Postgres; más ligero que Temporal si este pesa demasiado en el día a día |
| Hatchet | Descartada | Más ligero que Temporal, pero aporta menos como pieza de portafolio (tecnología menos usada en la industria) |
| Inngest / Prefect | Descartadas | Orientados a serverless y a pipelines de datos, no al patrón "dos tareas largas en paralelo con reintentos" |

## Consecuencias

**Positivas:**
- Reintentos (`RetryPolicy`), timeouts (`start_to_close_timeout`) y paralelismo
  (`asyncio.gather` de activities) declarativos, no código propio.
- El workflow continúa donde iba si el backend se reinicia; no se pierde trabajo.
- Historial completo y consultable en la Temporal Web UI por cada review.
- `workflow_id` determinista (`commit-{project}-{sha}`, `pr-{project}-{número}`) evita
  duplicar reviews del mismo commit.
- Debounce y cancelación nativos (`workflow.wait_condition` + cancelación de hijo) evitan
  lanzar una review por cada push en una ráfaga.

**Negativas / trade-offs:**
- Un servicio más que levantar y entender: Temporal server + UI, vía
  `temporal server start-dev` en desarrollo rápido o Docker Compose (perfil `infra` en
  este repo) para el entorno completo.
- Curva de aprendizaje inicial del modelo de workflows/activities/signals de Temporal.
- Mitigación: el plan B (DBOS) queda documentado aquí mismo si en algún momento el coste
  de mantener Temporal supera el valor que aporta; no se adopta salvo que eso ocurra.
