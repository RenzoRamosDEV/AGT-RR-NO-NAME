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
│   ├── domain/ application/ adapters/ workflows/ entrypoints/ fakes/
├── integration/   # Postgres real (testcontainers) y Temporal de test (salto de tiempo)
│   ├── persistence/   consultas, outbox, rollback, límites, esquema/migraciones
│   ├── concurrency/   escrituras simultáneas sobre la misma clave natural
│   ├── recovery/      worker ausente, fallo transitorio, acuse perdido, reintentos acotados
│   ├── workflows/     paralelismo, fallo parcial, deduplicación por workflow_id
│   └── regression/    un test por defecto ya corregido
└── fakes/         # repositorios y sesión en memoria usados por los tests
```

Los fixtures que necesitan infraestructura viven solo en `tests/integration/conftest.py`;
por eso `tests/unit` no importa nada de `adapters` ni necesita Docker (y `mutmut` puede aislar
`domain/` y `application/`). Los marcadores `unit`, `integration` y `regression` se aplican
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
| Regression tests | Cubierto | Marcador `regression`: agente desconocido = un solo intento, el diff no cruza Temporal (5 MB), `run` se propaga, estados guardados estables, deriva modelo/migración, NUL en eventos |
| Branch coverage | Cubierto | `--cov-branch`; umbrales global 97 % y `domain`+`application` 100 % (`just test` y CI) |
| Mutation testing | Cubierto | `mutmut` sobre `domain`+`application`, 243/243; `just mutation` y workflow semanal/manual `mutation.yml` |
| Property-based testing | Cubierto donde aporta | Invariantes de `Change`/`Review`, round-trip JSON de payloads, ley de idempotencia del repositorio, saneado de NUL. El resto usa ejemplos explícitos, más legibles |

### API y datos

| Tipo | Estado | Dónde / por qué |
| --- | --- | --- |
| Validación de contratos API | Diferido | Hoy solo existe `GET /health`. Contratos con `schemathesis` y snapshot de OpenAPI llegan con `POST /ingest/commit` → `expose-commit-ingestion` |
| Persistencia y consultas | Cubierto | `integration/persistence/`; `compare_metadata` garantiza que modelos y migraciones coinciden (ya destapó deriva real) y que son reversibles |
| Transacciones y rollback | Cubierto | Si falla el evento no queda ni el change ni la review |
| Autenticación y autorización | Diferido | No existe aún; llega con el token de ingesta → `expose-commit-ingestion` |
| Idempotencia | Cubierto | Integración, concurrencia, property-based y recuperación |

### Producción

| Tipo | Estado | Dónde / por qué |
| --- | --- | --- |
| E2E de flujos críticos | Parcial | El flujo interno (change persistido → workflow → dos reviews) está en `integration/workflows`. El E2E por HTTP espera al endpoint → `expose-commit-ingestion` |
| Security tests | Parcial | Inyección SQL como texto literal, NUL, límites y secretos (gitleaks y osv-scanner en CI). La seguridad de la API (cabeceras, comparación en tiempo constante, payloads hostiles por HTTP) espera al endpoint |
| Performance y load | Diferido | Riesgo bajo hoy y sin endpoint que cargar. El único riesgo real (diff enorme) ya está cubierto por la regresión de 5 MB. Prueba de carga de `POST /ingest/commit` → `expose-commit-ingestion` |
| Concurrencia | Cubierto | `integration/concurrency/` con Postgres real (`ON CONFLICT` bajo carrera) |
| Recovery tests | Cubierto | `integration/recovery/`: worker ausente, fallo transitorio, acuse perdido tras confirmar (at-least-once + idempotencia), reintentos acotados |

## Dónde va cada test nuevo

- Lógica pura sin I/O → `tests/unit/` (si toca una función de `domain`/`application`, la
  mutación te dirá si el assert es débil).
- Necesita Postgres o Temporal → `tests/integration/<tema>/`.
- Arregla un defecto → un test con el marcador `regression` y el origen en el docstring.
- Depende de la API HTTP → se añade al change que la introduce, no antes.
