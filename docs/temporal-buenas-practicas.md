# Temporal: cumplimiento del estándar de buenas prácticas

Matriz de Duelo frente al estándar técnico derivado de la documentación oficial de Temporal
(SPEC-WF/ACT/ERR/VER/OPS/TEST). Cada fila dice si se cumple, dónde está la evidencia (fichero o
test) o por qué no aplica. Rutas relativas a `backend/`. Change OpenSpec:
`temporal-workflow-good-practices`.

Leyenda: **Cumple** · **No aplica** (con motivo) · **Diferido** (con destino).

## SPEC-WF — Workflows

| Regla | Estado | Evidencia |
| --- | --- | --- |
| WF-1 Deterministas, sin I/O ni reloj propio | Cumple | `workflows/review_change.py`, `review_commit.py`: solo APIs del SDK, `asyncio.gather` sobre una lista; `render_details` es pura. Replays en `tests/integration/workflows/test_*_still_replays` |
| WF-2 Un único objeto de entrada | Cumple | `ReviewCommitInput`, `ReviewChangeInput`, `RunReviewInput` (`workflows/dto.py`), campos nuevos con valor por defecto |
| WF-3 Sin efectos en el workflow | Cumple | Toda persistencia y los CLI viven en `workflows/activities.py` |
| WF-4 Cambios de comandos bajo versionado | Cumple | `workflow.patched("compensate-infra-failure")`, `("readable-workflow-names")`; regla en `docs/adr/0007` |
| WF-5 Id de negocio determinista y política de reuso | Cumple | `application/workflow_naming.py`, `ALLOW_DUPLICATE_FAILED_ONLY` en `adapters/orchestration/temporal_review_starter.py` |
| WF-6 Tipo de versionado declarado | Cumple (en el ADR) | Auto-Upgrade documentado en `docs/adr/0007` y en los comentarios de los `@workflow.defn`; no se declara al SDK porque sin Worker Versioning el servidor real lo rechaza |
| WF-7 Continue-As-New fuera de handlers | No aplica | Sin señales ni Continue-As-New: los workflows duran minutos |
| WF-8 Historial > 1 000 eventos ⇒ Continue-As-New | No aplica | Un padre, un hijo y dos activities: < 50 eventos |
| WF-9 Señales/consultas por Workflow ID sin Run ID | Cumple | El starter consulta por id (`_legacy_execution_is_taken`); no hay señales |

## SPEC-ACT — Activities

| Regla | Estado | Evidencia |
| --- | --- | --- |
| ACT-1 Idempotentes con clave natural | Cumple | `uq_reviews_natural_key` + `on_conflict_do_nothing` (`adapters/persistence/review_repository.py`); `tests/integration/recovery/test_recovery.py`, `concurrency/` |
| ACT-2 `StartToClose` definido, sin timeouts infinitos | Cumple | `RUN_REVIEW_START_TO_CLOSE` 5 min y 1 min para la compensación (`application/review_timeouts.py`) |
| ACT-3 Sin reintentos manuales | Cumple | Ningún bucle de reintento en `adapters/agents/`; manda la `RetryPolicy` del workflow |
| ACT-4 Heartbeat en activities largas | Cumple | `heartbeat_timeout` 30 s y latidos cada 10 s (`workflows/activities.py`); `tests/unit/workflows/test_run_review_resilience.py` |
| ACT-5 Errores permanentes `non_retryable` | Cumple | Agente desconocido y change inexistente (`ApplicationError(non_retryable=True)`); el fallo del agente se registra como resultado, no como excepción |
| ACT-6 Activities pequeñas | Cumple | `run_review` y `record_review_infrastructure_failure`, una responsabilidad cada una |
| ACT-7 Payloads mínimos | Cumple | IDs y un extracto acotado (`application/payload_limits.py`); regresión «el diff no cruza Temporal» en `tests/integration/regression/` |

## SPEC-ERR — Errores y compensación

| Regla | Estado | Evidencia |
| --- | --- | --- |
| ERR-1 Compensación por paso | Cumple | `record_review_infrastructure_failure` cuando `run_review` agota sus intentos (`tests/integration/workflows/test_infrastructure_failure.py`) |
| ERR-2 Compensaciones idempotentes con su retry policy | Cumple | Misma clave natural y misma `RETRY`; «compensación repetida no duplica» en el mismo test |
| ERR-3 Retry policy por defecto explícita | Cumple | 3 intentos, 1 s, coeficiente 2, máximo 1 min (`application/review_timeouts.py` → `RETRY` en `review_change.py`); `tests/unit/workflows/test_retry_policy.py` |
| ERR-4 Rate limiting con `maximumInterval` mayor | No aplica | Los límites de uso de los CLI se registran como review fallida, no se reintentan |

## SPEC-VER — Versionado y despliegue

| Regla | Estado | Evidencia |
| --- | --- | --- |
| VER-1 Worker Versioning por defecto | No aplica (decisión) | Un worker por cola en la máquina del usuario, sin despliegues con varias versiones: parches + replay tests. `docs/adr/0007` |
| VER-2 Pinned / Auto-Upgrade según duración | Cumple | Auto-Upgrade (documentado, no declarado); es la única semántica posible al reiniciar `just worker` |
| VER-3 Replay tests en CI | Cumple | Historias grabadas en `tests/integration/workflows/legacy_*.py`; corren con `uv run pytest` en `.github/workflows/ci.yml` |
| VER-4 Sin Worker Versioning en colas por worker | No aplica | No hay Worker Versioning |

## SPEC-OPS — Workers y observabilidad

| Regla | Estado | Evidencia |
| --- | --- | --- |
| OPS-1 Una cola por carga; nombres en constantes | Cumple | `platform` y `agents` en `application/task_queues.py`; ningún literal en `src/` |
| OPS-1 ≥ 2 workers por cola | No aplica | Los CLI de los agentes están autenticados en una sola máquina; un segundo worker `agents` duplicaría el gasto de la suscripción |
| OPS-2 Apagado ordenado | Cumple | `SIGTERM`/`SIGINT` + `graceful_shutdown_timeout` (`worker.py`); `tests/unit/test_worker.py`, `tests/integration/workflows/test_worker_shutdown.py` |
| OPS-3 Métricas y alertas mínimas | Cumple | `TEMPORAL_METRICS_ADDRESS` expone las métricas del SDK (`tests/integration/workflows/test_worker_metrics.py`); alertas en `docs/architecture.md`, «Operación del worker» |
| OPS-4 Escalado por latencia × CPU | No aplica | Un worker local; la latencia schedule-to-start de las activities queda expuesta por si se despliega con más |
| OPS-5 Namespaces por entorno | Cumple | `TEMPORAL_NAMESPACE` en API y worker (`config.py`, `temporal_client.py`, `worker.py`); protección contra borrado e IaC son del servidor, fuera del repo |
| OPS-6 Search Attributes de negocio | Diferido | Exigen registrarlos en cada servidor (auto-setup, test env). Los resúmenes y fichas estáticos (`workflow-observability`) cubren la lectura operativa; se revisará si hace falta filtrar por proyecto en la UI de Temporal |

## SPEC-TEST — Pruebas

| Regla | Estado | Evidencia |
| --- | --- | --- |
| TEST-1 Tests de workflow con time-skipping | Cumple | `WorkflowEnvironment.start_time_skipping()` en `tests/integration/conftest.py`; `workflows/`, `recovery/`, `orchestration/`, `regression/` |
| TEST-2 Replay tests en CI | Cumple | Ver VER-3 |
| TEST-3 Failure injection, carga, game day | Parcial | Fallos inyectados en `recovery/` (worker ausente, persistencia transitoria, acuse perdido, permanente) y en `test_infrastructure_failure.py`; carga con `scripts/load_ingest.py` (`just load`); game day no aplica a un sistema de un solo usuario |

## Checklist de revisión de PR

Al tocar `backend/src/duelo/workflows/`, `worker.py` o los adaptadores de orquestación:

- [ ] ¿El workflow sigue sin I/O, reloj ni aleatorios propios (solo APIs del SDK)?
- [ ] ¿La entrada sigue siendo un único objeto con valores por defecto en los campos nuevos?
- [ ] ¿Cambió el orden o el número de activities, hijos o timers? → `workflow.patched` + historia
      grabada que lo reproduzca (`docs/adr/0007`).
- [ ] ¿Las activities siguen siendo idempotentes, con timeouts y heartbeat si son largas?
- [ ] ¿Los errores permanentes van como `non_retryable` y los transitorios por la `RetryPolicy`
      compartida (`application/review_timeouts.py`)?
- [ ] ¿Las task queues salen de `application/task_queues.py` (ningún literal nuevo)?
- [ ] ¿Un workflow nuevo con bucle o señales acota su historial (Continue-As-New) o justifica que
      no lo necesita?
- [ ] ¿`worker.py` sigue parándose por señal con plazo de gracia y sin abrir el puerto de métricas
      sin la variable?
- [ ] ¿Pasan `tests/integration/workflows` (replays incluidos) y `recovery`?
