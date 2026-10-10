# Estrategia de tests

Regla del proyecto: **solo se añaden los tipos de test que aportan valor sobre el código que
existe**. Lo que aún no se puede probar (porque no existe el código) no se rellena con tests
vacíos: se difiere con motivo explícito y queda como tarea de un change de OpenSpec.

La calidad no se mide con cobertura sino con **mutation testing**: al empezar, con 99 % de
cobertura, 59 de 206 mutantes sobrevivían (~71 %) porque nadie comprobaba que se reenviaran
campos como `agent`, `run` o `diff`. Hoy son 243 de 243 muertos.

## Capas

```
backend/tests/
├── unit/          # sin I/O, sin Docker, ~5 s: dominio, aplicación, adaptadores con fakes
│   ├── domain/ application/ adapters/ workflows/ entrypoints/ contract/ fakes/
├── e2e/           # API por HTTP + Postgres real + Temporal de test + workers (lo más lento)
├── integration/   # Postgres real (testcontainers) y Temporal de test (salto de tiempo)
│   ├── persistence/   consultas, outbox, rollback, límites, esquema/migraciones
│   ├── concurrency/   escrituras simultáneas sobre la misma clave natural
│   ├── recovery/      worker ausente, fallo transitorio, acuse perdido, reintentos acotados
│   ├── workflows/     paralelismo, fallo parcial, deduplicación por workflow_id
│   └── regression/    un test por defecto ya corregido
└── fakes/         # repositorios y sesión en memoria usados por los tests
```

Los fixtures que necesitan infraestructura viven solo en `tests/integration/conftest.py`;
por eso `tests/unit` no necesita Docker (los adapters se prueban ahí con mocks/fakes) y
`mutmut` puede limitarse a `domain/` y `application/`. Los marcadores `unit`, `integration` y `regression` se aplican
automáticamente por ruta (`tests/conftest.py`).

## Cómo ejecutar

| Receta | Qué hace |
| --- | --- |
| `just test-unit` | Capa unitaria, sin Docker, unos segundos. |
| `just test-integration` | Capa de integración (Docker o Podman; detecta Podman solo). |
| `just test` | Todo, con cobertura de ramas y umbrales (global 97 %, `domain`+`application` 100 %) y build del frontend. |
| `just mutation` | Mutation testing de `domain`+`application`; falla bajo 95 %. |
| `just ci` | Lint + tipos + capas + `just test` + validación de Compose. |
| `uv run pytest -m regression` | Solo los tests de regresión. |

Para una ejecución parcial con `pytest` directamente usa `--no-cov`: los umbrales de cobertura
son un paso explícito de `just test` y del CI, no de la configuración de pytest.
`HYPOTHESIS_PROFILE=ci` activa el perfil determinista de hypothesis (lo usa el CI).

## Mapa del checklist

Leyenda: **Cubierto** · **Parcial** (se prueba lo que existe; el resto está diferido) ·
**Diferido** (con motivo y destino).

### Lógica y requisitos

| Tipo | Estado | Dónde / por qué |
| --- | --- | --- |
| Unit tests | Cubierto | `tests/unit/**` |
| Particiones de equivalencia | Cubierto | Válido / vacío / demasiado largo / NUL por campo: `unit/domain/test_change_limits.py`, `test_review_agent_name.py`; los 4 resultados de `run_review` |
| Valores límite | Cubierto | n-1, n y n+1 de cada límite (unit) y los máximos reales contra Postgres: `integration/persistence/test_persistence_boundaries.py` |
| Casos negativos y excepciones | Cubierto | Identificadores inválidos con mensaje exacto, review fallida sin error, agente desconocido / change inexistente no reintentables, enums cerrados |
| Tablas de decisión | Cubierto | `unit/workflows/test_run_review_decision_table.py` (agente conocido × change existe × el agente lanza, con la precedencia) |
| Transiciones de estado | Parcial | Hoy `Change` solo tiene `pending` y `Review` es terminal e inmutable: `unit/domain/test_state_invariants.py`. La máquina `pending → reviewing → done/failed` llega con `finish_change`; testear transiciones inexistentes sería inventar un modelo |

### Calidad del código

| Tipo | Estado | Dónde / por qué |
| --- | --- | --- |
| Integration tests | Cubierto | `tests/integration/**` |
| Regression tests | Cubierto | Marcador `regression`: agente desconocido = un solo intento, el diff no cruza Temporal (5 MB), `run` se propaga, estados guardados estables, deriva modelo/migración, NUL en el payload de eventos |
| Branch coverage | Cubierto | `--cov-branch`; umbrales global 97 % y `domain`+`application` 100 % (`just test` y CI) |
| Mutation testing | Cubierto | `mutmut` sobre `domain`+`application`, 243/243; `just mutation` y workflow semanal/manual `mutation.yml` |
| Property-based testing | Cubierto donde aporta | Invariantes de `Change`/`Review`, round-trip JSON de payloads, ley de idempotencia del repositorio, saneado de NUL. El resto usa ejemplos explícitos, más legibles |

### API y datos

| Tipo | Estado | Dónde / por qué |
| --- | --- | --- |
| Validación de contratos API | Cubierto | `unit/contract/`: snapshot de `docs/openapi.json` (se regenera a propósito con `just openapi`) y `schemathesis` contra la app ASGI. Ya destapó un 400 no documentado (cuerpo no decodificable) |
| Persistencia y consultas | Cubierto | `integration/persistence/`; `compare_metadata` garantiza que modelos y migraciones coinciden (ya destapó deriva real) y que son reversibles; el predicado SQL del filtro `status` se contrasta con `review_status_from_counts` sobre toda la matriz de contadores (`test_review_status_queries.py`); la migración de `diff_summary` rellena por lotes y su copia congelada del algoritmo se contrasta con `summarize_diff` (`test_migrations.py`); resumen del diff, stats por proyecto, review por id y eventos en `test_round3_persistence.py` (los eventos salen por `created_at` y desempata el `id`, con filas de fechas cruzadas); los índices del canal existen, la migración `d4a8e1b5c602` sube y baja, y un EXPLAIN de la consulta real con 8 000 changes comprueba que recorre el índice y cuenta reviews sin `Seq Scan` ni `Sort` (`test_channel_indexes.py`); `stale` con reloj inyectado en `test_stale_api.py` y el umbral exacto en `unit/domain/test_review_status.py`; las reviews ligeras del canal (solo run actual, sin columnas pesadas y dos consultas con 5 changes, sin N+1) en `test_read_queries.py` y su contrato en `unit/entrypoints/test_channel_reviews_api.py`, junto con `agent_names` del diagnóstico |
| Resiliencia de workflows (fallo de infraestructura y latidos) | Cubierto | Con Temporal de test y Postgres real (`integration/workflows/test_infrastructure_failure.py`): un agente cuya persistencia falla en los 3 intentos queda con una review `failed` de mensaje genérico mientras el otro completa; con todos fallando el change queda `failed` y por tanto reintentable; la compensación repetida no duplica fila ni evento; el parche deja su marcador en el historial y **un historial anterior (workflow sin compensación, en `legacy_review_change.py`) se reproduce con el workflow nuevo sin no-determinismo** (sin `workflow.patched` ese test falla con `NondeterminismError`). Latidos y compensación como funciones, con el latido y el intervalo inyectados (`unit/workflows/test_run_review_resilience.py`: ≥3 latidos con un agente lento, se detienen al volver o al lanzar, no-op fuera de una activity). `run_started_at`: la migración rellena desde `created_at` y es reversible, la ingesta lo iguala a la creación, `advance_run` lo guarda, y un reintento limpia `stale` de un change antiguo (`integration/persistence/test_run_started_at.py`, `unit/entrypoints/test_stale_api.py`) |
| Lo que se ve en Temporal (nombres, respuestas, resúmenes) | Cubierto | Funciones puras con expectativas exactas y un caso por regla (`unit/application/test_workflow_naming.py`: saneado del repo, corte a 60 caracteres sin separador colgante, id por tipo y `run`, **proyecto quitado y vuelto a añadir con el mismo nombre ⇒ otro id**, **un commit y una PR con el mismo SHA ⇒ ids de hijo distintos (regresión que destapó el e2e de lectura; también con Temporal y workers reales en `test_readable_workflows.py`)**, markdown y HTML sin efecto; `test_payload_limits.py`: cortes, saneado de control y credenciales, incluido `Authorization: Bearer …` que antes dejaba el token a la vista). El extracto de la review (`unit/workflows/test_review_result_payload.py`: límites exactos con y sin corte, total real de hallazgos, error saneado, **sin `raw_output`**, ida y vuelta por el conversor de Temporal y un resultado anterior que se sigue deserializando) y el texto de «Current Details» (`test_review_details.py`: pendiente, completada, fallida, desglose por severidad, recortes y un agente hostil). Con Temporal de test y Postgres real: el **historial** de las ejecuciones tiene el resultado de cada actividad con resumen, nota y hallazgos, los resúmenes de las actividades, el resumen y la ficha estáticos de padre e hijo, y los «Current Details» (`integration/workflows/test_readable_workflows.py`); nombres `commit-…`/`pr-…`/`review-…` y la **guarda del id antiguo** (en marcha, ya revisado ⇒ no se arranca otra; fallido ⇒ sí; el `-r2` con su propio id; sin ella fallan 3 tests) en `integration/orchestration/test_readable_names.py`. **Replay:** historias grabadas con el workflow anterior (padre con hijo `review-{change}-r{run}` y hijo sin compensación) se reproducen con el nuevo sin no determinismo. Medido: el replay pasa aun sin `workflow.patched` porque las historias antiguas no traen los datos de presentación en la entrada (es lo que las protege) y los metadatos de usuario no se comparan al reproducir; el marcador queda como cinturón y tirantes. Contra Temporal **real** (a mano, fuera de la CI): 1.24.2 descarta los metadatos de usuario; 1.26.2 los guarda; la UI 2.36.1 los muestra; la actualización 1.24.2 → 1.26.2 conserva los workflows anteriores |
| Agentes de CLI reales (`claude`, `codex`) | Cubierto, y los CLI reales opcionales | Unitarios con un runner de subprocesos falso (`tests/fakes/cli_runner.py`): argumentos exactos de **solo lectura y confinados** (Claude con `--restricted`; Codex con `--ignore-user-config`, `--ignore-rules` y las 30 funciones desactivadas (shell, lectura de disco o workspace, subagentes, red, plugins, MCP); sin Bash/Edit/Write ni modos que se salten permisos), prompt por stdin y no en los argumentos, diff hostil delimitado como dato no confiable, esquema y parseo estricto (rangos, tipos, límites), **salida truncada o por encima del límite rechazada en vez de parseada recortada**, binario ausente, sin sesión, plazo vencido, mensajes de error fijos que no filtran la salida del CLI ni rutas, entorno sin secretos de Duelo ni claves de API, directorio de trabajo (carpeta del proyecto solo para Claude; Codex siempre un temporal vacío 0700 que se borra), ficheros temporales 0600 borrados siempre, tope de concurrencia compartido y registro por nombre. `run_command`: stdin, variables excluidas, límite de salida con `truncated`, el bucle de eventos no se bloquea, un **descendiente desasociado que retiene el pipe no cuelga el plazo** (regresión), y cancelar la llamada mata el programa y libera el transporte aunque un nieto retenga los pipes. Clasificación de las funciones de Codex: lógica con salida falsa de `codex features list` y un test contra el `codex` real (no consume suscripción; falla nombrando la función si una versión nueva trae una habilitada sin clasificar). Configuración: `AGENT_TIMEOUT_SECONDS` ≤ 270 s (activity − 30 s, constante compartida con el workflow). Con Postgres y Temporal de test: la ruta del proyecto (`path_of`) y el tope `max_concurrent_activities` del worker. Con los **CLI reales** (`tests/integration/agents/`, marcador `cli_agents`): solo con `RUN_CLI_AGENT_TESTS=1`, porque consumen la suscripción; no corren en la CI. Comprueban que el formato real de salida sigue encajando con los parsers y que, con los argumentos reales de cada agente, un prompt que pide leer o ejecutar fuera del directorio no obtiene nada. |
| Transacciones y rollback | Cubierto | Si falla el evento no queda ni el change ni la review |
| Autenticación y autorización | Cubierto | `unit/entrypoints/test_ingest_api.py`: token ausente, vacío, con espacios, otra capitalización, otra longitud, no ASCII → 401 sin efectos; `/health` y `/ready` abiertos; espía sobre `hmac.compare_digest`. Dos secretos: el de ingesta y `OPERATOR_TOKEN` para la salida cruda (`test_round3_api.py`: deshabilitado → 404 para todos, el token de ingesta no vale, sin `raw_output` en ninguna otra respuesta; `test_config.py`: distinto del de ingesta y mínimo 16 caracteres) |
| Idempotencia | Cubierto | Integración, concurrencia, property-based y recuperación |

### Producción

| Tipo | Estado | Dónde / por qué |
| --- | --- | --- |
| Proyectos locales y hooks de git | Cubierto | Con **repos git reales y temporales** (no mocks de git): el slug desde cualquier forma de remoto (`unit/domain/test_project_slug.py`); alta, baja y sincronización con fakes de los puertos, con la compensación si fallan los hooks y la baja que quita los hooks antes de borrar y se conserva si fallan (`unit/application/test_local_projects.py`); validación de rutas (relativa, `..`, NUL, enlace simbólico, subcarpeta, worktree), instalador de hooks (bloque tras el shebang, hook previo intacto y restaurado byte a byte, idempotencia, `core.hooksPath` fuera del repo rechazado, hook que no es shell rechazado sin escribir nada, vuelta atrás si falla una escritura, comillas del shell con slug hostil, stdin del `pre-push` para los hooks posteriores), runner de subprocesos (sin shell, plazo, mata también a los hijos) y `gh` simulado en el `PATH` (`unit/adapters/git/`, `unit/adapters/github/`, `unit/adapters/test_subprocess_runner.py`); el hook ignora `INGEST_URL`/`INGEST_TOKEN` del entorno (con un «atacante» local que no recibe nada), rechaza URLs no http(s) y funciona con una `HOOK_ENV_PATH` distinta de XDG y HOME; el hook no sigue ningún 301/302/303/307/308: un servidor «espía» en otro puerto no recibe ni la petición ni el token (`test_hook.py`); el módulo del hook como proceso real: vuelve en menos de 3,5 s con la API lenta o caída, sale con 0, y un `git commit` y un `git push` reales llegan a un servidor HTTP local (`unit/entrypoints/test_hook.py`); API desactivada → 404 sin token, 401, 201/409/422/204/503 y límite de peticiones (`test_local_projects_api.py`); sincronizador periódico y ciclo de vida (`test_background.py`); restricciones únicas, carrera de altas de la misma carpeta y cascada del borrado contra Postgres (`integration/persistence/test_local_projects_persistence.py`) y migración reversible que conserva proyectos previos (`test_migrations.py`). `tests/unit/conftest.py` aísla git de la configuración del usuario. Diferido: Windows (el hook sin `fork` envía en el propio proceso con un plazo de 2 s) |
| Reutilización de las reviews del commit en la PR | Cubierto | Decisión pura con tabla de casos (`unit/domain/test_review_reuse.py`: mismo diff sí; diff, SHA, `diff_truncated`, proyecto o tipo distintos no; falta un agente, review fallida y run anterior no; agentes no esperados ignorados), caso de uso con fakes (`unit/application/test_ingest_pr_reuse.py`: nace `completed` sin starter, reenvío sin copias, reintento = PR normal, commit nunca reutiliza), contrato HTTP (`unit/entrypoints/test_pr_reuse_api.py`: `reused`, `reused_from`, evento `review.reused`), Postgres real (`integration/persistence/test_review_reuse.py`: copia atómica, idempotencia, 6 ingestas simultáneas, rollback si falla una inserción, `SET NULL` al borrar el commit, migración arriba y abajo) y e2e con Temporal y workers reales (`e2e/test_pr_reuse_flow.py`: la PR nace con 2 reviews copiadas y **sin workflow**; con otro diff se revisa normal). El integración cazó un fallo que los fakes no veían: leer con la transacción implícita abierta hacía fallar el `add` siguiente. Rompiendo a propósito el arranque condicionado fallan 3 tests |
| Commits deshechos y revertidos | Cubierto | Reglas puras con conjuntos, ventana y una propiedad de `hypothesis` (nunca descarta un alcanzable ni restaura uno ausente): estado y precedencia, lectura estricta del mensaje de `git revert` (formato real, párrafos sueltos, SHA corto, mayúsculas y título ajeno no cuentan), SHA seguro como argumento de git (`unit/domain/test_commit_state.py`); el barrido con historial y marcas falsos: marca, restaura, idempotencia, ventana llena con confirmación individual, repo roto sin marcar y orden «changes antes que git» (`unit/application/test_reachability.py`); la ingesta del revert en cualquier orden, varios reverts, revert deshecho y `amend` (`test_ingest_revert.py`); el adaptador contra **repos git reales**: `reset`, `amend`, rama borrada, cabeza desacoplada, etiqueta, ref remota, ventana, carpeta o git ausentes, carpeta sustituida por un enlace simbólico, subcarpeta, repositorio distinto, un repo hostil que no ejecuta su `fsmonitor` y un SHA que no es hexadecimal sin llegar nunca a git (`unit/adapters/git/test_history.py`); el hook envía el `body` de un `git revert` real (`test_hook.py`); contrato HTTP y eventos (`test_commit_state_api.py`); configuración y cableado de la tarea de fondo (`test_config.py`, `unit/test_composition_jobs.py`). Con Postgres real: migración arriba y abajo, marcas atómicas, dos barridos simultáneos, el LATERAL del revert sin consultas extra y la integridad al borrar (`integration/persistence/test_commit_state.py`, que destapó un `JOIN` ambiguo que los fakes no veían). E2E con uvicorn, git y hooks reales y el barrido a 1 s: `reset`, vuelta atrás, `git revert`, deshacer el revert y `--amend` del revert (`e2e/test_commit_state_flow.py`). Diferido: repos de más de 100 000 commits (la ventana llena se prueba con una ventana pequeña) |
| E2E de flujos críticos | Cubierto | `tests/e2e/`: ASGI + Postgres + Temporal de test + workers reales. Camino feliz (dos reviews), reingesta sin duplicados, proyecto inexistente, Temporal caído → 503 y reenvío que arranca la review, diff recortado; lecturas (canal paginado, detalle, métricas) tras ingerir un PR y un commit con el mismo sha, y reintento de una review fallida con filtros, `run` 2 real y `/health/dependencies`; `created` en la ingesta, `diff_summary`, stats por proyecto, eventos y salida cruda de operador (`test_read_flow.py`). Verificado además a mano contra Temporal real; `test_local_projects_flow.py` levanta uvicorn de verdad y comprueba que tras dar de alta una carpeta un `git commit` y un `git push` reales llegan al canal con sus dos reviews, que la baja deja los hooks como estaban y que `sync-prs` registra las PRs de un `gh` simulado |
| Security tests | Cubierto | Inyección SQL y HTML como texto literal, NUL, límites, cuerpos malformados → 422 sin traza, token y detalles internos fuera de respuestas y logs; gitleaks y osv-scanner en CI. Rate limit de ingesta y reintento (`unit/entrypoints/test_rate_limit_api.py`: 429 con `Retry-After`, grupos independientes, token inválido también gasta cupo, ventana deslizante) y CORS cerrado por defecto (`test_cors.py`: sin `*`, sin credenciales, `X-Operator-Token` no permitido desde navegador); el access log no contiene query, cuerpo ni tokens (`test_request_context.py`). Tamaño del cuerpo de la ingesta (`test_body_limit.py`): 413 por `Content-Length` sin tocar la aplicación, por conteo del flujo sin `Content-Length`, límite inclusivo al byte, antes del token y con `X-Request-ID`, otras rutas intactas, el cuerpo nunca en la respuesta ni en el log, y un uvicorn real al que se suben 6 MB (con y sin `Content-Length`) y que sigue sirviendo después. Pendiente a futuro: cabeceras de seguridad y autenticación de lectura si la API sale de `127.0.0.1`; el límite es en memoria de un proceso |
| Performance y load | Cubierto | `just load` (`scripts/load_ingest.py`, bajo demanda): presupuesto 0 errores y p95 ≤ 300 ms con 5 clientes. Primera medición contra Temporal y Postgres reales: 200 peticiones, 109 req/s, p50 41 ms, p95 70 ms, 0 errores (el límite por defecto, 300 por minuto, no la afecta; con más peticiones hay que arrancar con `RATE_LIMIT_REQUESTS=0`). Más la regresión del diff de 5 MB |
| Concurrencia | Cubierto | `integration/concurrency/` con Postgres real (`ON CONFLICT` bajo carrera); `advance_run` (compare-and-swap) con 8 peticiones simultáneas y un único ganador, y dos reintentos intercalados en los unit tests |
| Recovery tests | Cubierto | `integration/recovery/`: worker ausente, fallo transitorio, acuse perdido tras confirmar (at-least-once + idempotencia), reintentos acotados |

## Dónde va cada test nuevo

- Lógica pura sin I/O → `tests/unit/` (si toca una función de `domain`/`application`, la
  mutación te dirá si el assert es débil).
- Necesita Postgres o Temporal → `tests/integration/<tema>/`.
- Arregla un defecto → un test con el marcador `regression` y el origen en el docstring.
- Depende de la API HTTP → `tests/unit/entrypoints/` con `tests/fakes/api.py` (`build_fake_api`, sin I/O); el flujo completo con infraestructura va en `tests/e2e/`.
