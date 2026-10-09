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
| Persistencia y consultas | Cubierto | `integration/persistence/`; `compare_metadata` garantiza que modelos y migraciones coinciden (ya destapó deriva real) y que son reversibles |
| Transacciones y rollback | Cubierto | Si falla el evento no queda ni el change ni la review |
| Autenticación y autorización | Cubierto | `unit/entrypoints/test_ingest_api.py`: token ausente, vacío, con espacios, otra capitalización, otra longitud, no ASCII → 401 sin efectos; `/health` y `/ready` abiertos; espía sobre `hmac.compare_digest`. No hay roles: un único token de ingesta |
| Idempotencia | Cubierto | Integración, concurrencia, property-based y recuperación |

### Producción

| Tipo | Estado | Dónde / por qué |
| --- | --- | --- |
| E2E de flujos críticos | Cubierto | `tests/e2e/`: ASGI + Postgres + Temporal de test + workers reales. Camino feliz (dos reviews), reingesta sin duplicados, proyecto inexistente, Temporal caído → 503 y reenvío que arranca la review, diff recortado; lecturas (canal paginado, detalle, métricas) tras ingerir un PR y un commit con el mismo sha (`test_read_flow.py`). Verificado además a mano contra Temporal real |
| Security tests | Cubierto | Inyección SQL y HTML como texto literal, NUL, límites, cuerpos malformados → 422 sin traza, token y detalles internos fuera de respuestas y logs; gitleaks y osv-scanner en CI. Pendiente a futuro: rate limiting y cabeceras si la API sale de `127.0.0.1` |
| Performance y load | Cubierto | `just load` (`scripts/load_ingest.py`, bajo demanda): presupuesto 0 errores y p95 ≤ 300 ms con 5 clientes. Primera medición contra Temporal y Postgres reales: 200 peticiones, 109 req/s, p50 41 ms, p95 70 ms, 0 errores. Más la regresión del diff de 5 MB |
| Concurrencia | Cubierto | `integration/concurrency/` con Postgres real (`ON CONFLICT` bajo carrera) |
| Recovery tests | Cubierto | `integration/recovery/`: worker ausente, fallo transitorio, acuse perdido tras confirmar (at-least-once + idempotencia), reintentos acotados |

## Dónde va cada test nuevo

- Lógica pura sin I/O → `tests/unit/` (si toca una función de `domain`/`application`, la
  mutación te dirá si el assert es débil).
- Necesita Postgres o Temporal → `tests/integration/<tema>/`.
- Arregla un defecto → un test con el marcador `regression` y el origen en el docstring.
- Depende de la API HTTP → `tests/unit/entrypoints/` con `tests/fakes/api.py` (`build_fake_api`, sin I/O); el flujo completo con infraestructura va en `tests/e2e/`.
