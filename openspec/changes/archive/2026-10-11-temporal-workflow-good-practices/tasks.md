# Tasks

## 1. Constantes y política de reintentos

- [x] 1.1 Crear `application/task_queues.py` (`PLATFORM_TASK_QUEUE`, `AGENTS_TASK_QUEUE`) y usarlo en `worker.py`, `temporal_review_starter.py`, `review_change.py` y en los tests que construyen `Worker`. Verificación: `grep -rn '"platform"\|"agents"' backend/src` sin resultados y `just test-unit` en verde.
- [x] 1.2 Añadir a `application/review_timeouts.py` los primitivos de reintento (3 intentos, 1 s, coeficiente 2, 1 min) y construir `RETRY` en `review_change.py` con ellos; test unitario que comprueba los cuatro valores de la política del workflow. Verificación: el test pasa y `tests/integration/recovery` sigue en verde (fallo transitorio → una sola review; permanente → 3 intentos).

## 2. Configuración: namespace y métricas

- [x] 2.1 `WorkerSettings.temporal_namespace` (`default`) y `temporal_metrics_address` (`None`); `LazyTemporalClient(address, namespace)` y `composition.py` lo pasan; test unitario de `config` (valores por defecto y desde el entorno) y de `LazyTemporalClient` (pasa `namespace` a `Client.connect`). Verificación: `just test-unit`.
- [x] 2.2 `build_runtime(settings)` en `worker.py` (`PrometheusConfig` solo con la variable) y `Client.connect(..., namespace, runtime)`; test de integración: con la dirección en un puerto libre, tras una review `GET /metrics` contiene `temporal_` (schedule-to-start / slots), y sin la variable `build_runtime` devuelve `None`. Verificación: `just test-integration -k metrics`.

## 3. Apagado ordenado

- [x] 3.1 `run_until_signalled(workers, stop)` + `install_stop_signals(loop, stop)` en `worker.py`, `graceful_shutdown_timeout` desde `WORKER_SHUTDOWN_GRACE_SECONDS` (30 s, `ge=0`); test unitario que envía `SIGTERM` al propio proceso y comprueba que la función retorna y los contextos se cierran. Verificación: `just test-unit`.
- [x] 3.2 Test de integración con Temporal de test: un agente lento, `shutdown()` del worker con plazo corto → la llamada al agente se cancela, no se persiste review, y un worker nuevo completa la review una sola vez; y con un agente que termina dentro del plazo la review queda persistida. Verificación: `just test-integration -k shutdown`.
- [x] 3.3 Documentar las variables nuevas en `docs/architecture.md` y en la cabecera de `worker.py`. Verificación: la tabla de variables incluye `TEMPORAL_NAMESPACE`, `TEMPORAL_METRICS_ADDRESS` y `WORKER_SHUTDOWN_GRACE_SECONDS`.

## 4. Versionado y documentación del estándar

- [x] 4.1 `docs/adr/0007-versionado-de-workflows.md` (parches + replay tests, Auto-Upgrade, por qué no Worker Versioning, regla de retirada de marcadores) y `versioning_behavior=AUTO_UPGRADE` en los dos `@workflow.defn`. Verificación: `tests/integration/workflows` (incluidos los replays de historias grabadas) en verde.
- [x] 4.2 `docs/temporal-buenas-practicas.md` con la matriz SPEC-WF/ACT/ERR/VER/OPS/TEST → estado y evidencia (fichero o test), más las alertas mínimas con umbrales; enlazarla desde `docs/architecture.md` y añadir la fila a `docs/testing.md`. Verificación: cada fila de la matriz apunta a un fichero o test existente.
- [x] 4.3 Ampliar el checklist de `.claude/skills/temporal-review/SKILL.md` (historial/Continue-As-New, métricas y apagado, constantes de cola, política de reintentos compartida). Verificación: el fichero incluye los cuatro puntos.

## 5. Cierre

- [x] 5.1 `just ci` en verde (lint, tipos, capas, tests con umbrales, compose) y revisión del change con Codex (`codex exec` en modo lectura) atendiendo sus hallazgos. Verificación: salida de `just ci` y resumen de la revisión en el informe final.

## Workflow follow-up

- Archivar el change (`openspec archive`) y commit/PR cuando el usuario lo pida.
