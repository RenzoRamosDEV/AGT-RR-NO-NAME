# Design

## Context

Ver `proposal.md` (Why). Estado observado:

- `worker.py` hace `Client.connect(address)` y espera en `asyncio.Event().wait()`: sin manejo de
  señales ni `graceful_shutdown_timeout`. Con `asyncio.run`, `SIGINT` lanza `KeyboardInterrupt`
  (sale por el `async with` con cancelación inmediata) y `SIGTERM` mata el proceso sin más; el CLI
  del agente puede quedar huérfano y Temporal tarda `heartbeat_timeout` (30 s) en darse cuenta.
- `LazyTemporalClient` y el worker usan el namespace `default` implícito. No hay `Runtime` propio
  ni telemetría. `WorkerSettings` (`config.py`) es la fuente de configuración de API y worker.
- `RETRY = RetryPolicy(maximum_attempts=3, initial_interval=1s)` en `workflows/review_change.py`
  deja `backoff_coefficient` 2 y `maximum_interval` 100 s implícitos. Los plazos viven en
  `application/review_timeouts.py` (sin dependencias de Temporal; `application/` no importa
  `temporalio` y la contratación de capas de `import-linter` lo prohíbe de hecho).
- `"platform"` y `"agents"` aparecen como literales en `worker.py`, `temporal_review_starter.py`
  y `review_change.py` (y en ~30 sitios de los tests).
- Versionado: `workflow.patched` con dos marcadores y replay tests sobre historias grabadas
  (`tests/integration/workflows/legacy_*.py`). `temporalio` 1.34 acepta
  `@workflow.defn(versioning_behavior=VersioningBehavior.AUTO_UPGRADE)` sin `deployment_config`
  (comprobado con el servidor de test: el servidor lo ignora si no hay Worker Versioning).
- No hay servicio de worker en `docker-compose.yml`: el worker corre con `just worker` en la
  máquina del usuario (restricción del proyecto: los CLI están ahí autenticados).

## Goals / Non-Goals

**Goals:**
- Cerrar los huecos OPS-1/2/3/5, ERR-3 y WF-6/VER-1 del estándar sin cambiar ids, historial ni
  contratos de los workflows (ninguna ejecución en vuelo debe verse afectada).
- Cada cambio verificable con un test del nivel adecuado o con un comando documentado.

**Non-Goals:**
- Worker Versioning con despliegues *rainbow*, ≥2 workers por cola, escalado por latencia×CPU y
  Temporal Cloud: no aplican a un worker único en la máquina del usuario; quedan en la matriz
  como «no aplica» con el motivo.
- Search Attributes de negocio: exigen registrarlos en el servidor (auto-setup, test env y
  cualquier despliegue) y los resúmenes estáticos ya cubren la lectura operativa.
- Continue-As-New: los workflows duran minutos y tienen < 50 eventos.
- OpenTelemetry/structlog en el worker: la pila lo prevé, pero es otro change; aquí solo el
  endpoint Prometheus que el SDK trae sin dependencias nuevas.

## Decisions

1. **Constantes de task queue en `application/task_queues.py`** (`PLATFORM_TASK_QUEUE`,
   `AGENTS_TASK_QUEUE`). Van en `application/` porque las usan a la vez `adapters/` y
   `workflows/` (capas hermanas que no pueden importarse) — el mismo motivo que
   `review_timeouts.py`. Los tests pasan a usarlas también. Alternativa: dejarlas en
   `workflows/` e importarlas desde el starter; descartada por la regla de capas.

2. **Apagado ordenado en `worker.py`.** `main()` crea un `asyncio.Event`, instala
   `loop.add_signal_handler(SIGINT|SIGTERM, stop.set)` y espera `stop.wait()` dentro del
   `async with platform, agents`; ambos `Worker` reciben
   `graceful_shutdown_timeout=timedelta(seconds=settings.worker_shutdown_grace_seconds)`
   (`WORKER_SHUTDOWN_GRACE_SECONDS`, 30 s por defecto, `ge=0`). Con el SDK, al salir del
   `async with` el worker deja de hacer *polling*, espera ese plazo y cancela las activities que
   sigan: `run_review` recibe la cancelación mientras espera a `agent.review`, los agentes CLI ya
   matan su grupo de procesos al cancelarse, `CancelledError` no lo atrapa el `except Exception`,
   así que no se persiste nada y Temporal reintenta la activity por la política normal cuando
   vuelve un worker. El plazo por defecto es 30 s (el mismo margen que
   `AGENT_TIMEOUT_MARGIN`): más largo haría esperar a `podman stop`/systemd sin beneficio, porque
   una review no suele terminar en ese tiempo. La lógica de señal se separa en una función
   (`run_until_signalled(workers, signals)`) para testearla sin Temporal.
   Alternativa: capturar `KeyboardInterrupt`; descartada porque no cubre `SIGTERM`.

3. **Namespace y métricas en `WorkerSettings`.** `temporal_namespace: str = "default"` y
   `temporal_metrics_address: str | None = None`. `LazyTemporalClient(address, namespace)` y el
   worker pasan `namespace=` a `Client.connect`. Solo el worker construye un
   `Runtime(telemetry=TelemetryConfig(metrics=PrometheusConfig(bind_address=…)))` y se lo pasa a
   `Client.connect(runtime=…)`: las métricas pedidas (schedule-to-start, slots, fallos) son del
   worker, y un `Runtime` con Prometheus abre un puerto, cosa que la API no debe hacer por una
   variable pensada para el worker. La construcción del runtime se aísla en una función
   (`build_runtime(settings) -> Runtime | None`) para probarla.
   Alternativa: OpenTelemetry (`OpenTelemetryConfig`); descartada aquí por necesitar un
   colector; se deja apuntada para el change de observabilidad.

4. **Política de reintentos: primitivos en `application/review_timeouts.py`, `RetryPolicy` en
   `workflows/review_change.py`.** `RUN_REVIEW_RETRY_MAX_ATTEMPTS = 3`,
   `RUN_REVIEW_RETRY_INITIAL = 1 s`, `RUN_REVIEW_RETRY_BACKOFF = 2.0`,
   `RUN_REVIEW_RETRY_MAX_INTERVAL = 1 min`; el workflow construye `RETRY` con ellos y la
   compensación usa la misma. Cambiar las opciones de reintento de una activity es un cambio
   seguro para ejecuciones en vuelo (no produce comandos distintos). Alternativa: importar
   `RetryPolicy` en `application/`; descartada por la regla de capas.

5. **Versionado: ADR 0007 «parches y replay tests en vez de Worker Versioning».** Se declara
   `versioning_behavior=VersioningBehavior.AUTO_UPGRADE` en los dos `@workflow.defn` (documenta
   el tipo que exige WF-6 y es inocuo sin `deployment_config`) y el ADR fija la regla: cada cambio
   de comandos va bajo `workflow.patched` con una historia grabada que lo pruebe, y los marcadores
   se retiran con `deprecate_patch` cuando no quede ninguna ejecución anterior. Worker Versioning
   se descarta porque exige despliegues con varias versiones de worker a la vez; Duelo tiene un
   worker por cola en una máquina. Los replay tests existentes deben seguir pasando con la
   declaración (lo verifica la suite de integración).

6. **Docs.** `docs/temporal-buenas-practicas.md` con la matriz SPEC → estado (cumple / cómo /
   no aplica y por qué), enlazada desde `docs/architecture.md`; variables nuevas en la tabla;
   alertas mínimas (OPS-3) con umbrales orientativos; checklist de PR en la skill
   `temporal-review` (Continue-As-New/historial, métricas y apagado, constantes de cola).

## Risks / Trade-offs

- [Cancelar una review al apagar gasta un intento de los 3] → aceptado: el reintento ocurre al
  volver el worker y, si el apagado se repite 3 veces, la compensación deja la review `failed`
  y el change reintentable, como hoy.
- [`add_signal_handler` no existe en Windows] → el worker solo corre en Linux/macOS (los CLI);
  se protege con `NotImplementedError` → fallback a esperar sin señales.
- [Puerto de métricas ocupado] → el `Runtime` falla al arrancar con un error claro; la variable
  es opcional.
- [`versioning_behavior` en un servidor que sí tenga Worker Versioning] → se activaría
  Auto-Upgrade, que es la semántica elegida; documentado en el ADR.
- [Cambiar los literales de task queue en los tests es ruido] → se cambian solo en `src/` y en
  los tests que construyen `Worker` (con las constantes), no en los que comprueban nombres.

## Migration Plan

Sin migración: ids, historial, DTOs y base de datos no cambian. Despliegue: reiniciar API y
worker; las variables nuevas son opcionales. Rollback: volver al commit anterior.
