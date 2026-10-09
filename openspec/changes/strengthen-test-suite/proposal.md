# Proposal

## Por qué

La suite actual (96 tests) tiene 99 % de cobertura de líneas y ramas, pero eso no mide la
calidad de los asserts. Una auditoría contra el checklist de tipos de test lo demuestra:

- **Mutation testing (mutmut) sobre `domain/` y `application/`: 206 mutantes, 59
  supervivientes (~71 % de puntuación).** Los supervivientes son siempre el mismo patrón:
  ningún test comprueba que se *propaguen* los campos (`agent=None`, `url=None`, `run=None`
  o `id=None` pasan todos los tests). Se podría romper el reenvío de un campo sin que nada
  falle.
- La rama "el `Change` no existe" de `run_review` nunca se ejecuta en los tests.
- Los fixtures de Postgres/testcontainers están en el `conftest.py` raíz: todo test, incluso
  uno puro de dominio, importa infraestructura. Eso impide medir mutación de `domain/` y
  `application/` (el entorno aislado no contiene `adapters/`) y mezcla tests de
  milisegundos con tests de contenedor.
- No hay tests de concurrencia ni de recuperación, y el esquema de BD y los modelos
  SQLAlchemy no se contrastan entre sí.

Regla del proyecto: se añaden solo los tipos de test que aportan valor sobre el código que
existe hoy; lo que depende de la API HTTP (contratos, autenticación, seguridad de API, E2E,
carga) se difiere con motivo explícito a `expose-commit-ingestion`, que es donde
aparece ese código. Un primer sondeo de límites ya produjo un change aparte
(`harden-input-limits`, archivado) que corrigió defectos reales de persistencia.

## Qué cambia

- **Reorganización de la suite** en `tests/unit/` (sin I/O, milisegundos) y
  `tests/integration/` (Postgres real y/o Temporal de test), con marcadores automáticos
  `unit`/`integration`, y marcador `regression`. Los fixtures de contenedor pasan a
  `tests/integration/conftest.py`.
- **Lógica y requisitos:** tests de propagación de campos (matan los mutantes), tabla de
  decisión de `run_review` (agente conocido × change existente × el agente falla), casos
  negativos que faltaban, e invariantes de inmutabilidad/terminalidad de `Review`.
- **Property-based (hypothesis)** donde aporta: invariantes de `Change`/`Review`, round-trip
  JSON de los payloads de eventos y la ley de idempotencia del repositorio.
- **Persistencia y datos:** `get()` y lectura de reviews con `findings` contra Postgres,
  orden de los eventos del outbox, rollback transaccional de la review, y que el
  esquema de las migraciones coincida con los modelos (`compare_metadata`), incluida la
  reversibilidad `upgrade → downgrade → upgrade`.
- **Concurrencia (Postgres real):** ingestas simultáneas de la misma clave natural,
  registros simultáneos de la misma review y ráfagas de claves distintas.
- **Recuperación (Temporal):** el workflow espera y termina cuando el worker de agentes
  vuelve tras estar caído, y la review sigue siendo única si la persistencia falla
  transitoriamente o se pierde el acuse tras confirmar (entrega *at-least-once* con
  idempotencia).
- **Regresión:** un test nombrado por cada defecto ya corregido (agente desconocido sin
  reintentos, el diff no viaja por Temporal, estados guardados con valores estables).
- **Cobertura de ramas con umbrales** (global y más estricto en `domain/` y
  `application/`) y **mutation testing** (`just mutation`, umbral de puntuación) en un
  workflow programado/manual, no en cada push.
- **`docs/testing.md`:** mapa del checklist (cubierto / añadido / diferido con motivo) y
  guía de qué test va en qué capa.
- **Contraste con Codex** de la estrategia y de los tests, y corrección del código o de los
  tests donde proceda.

Diferido (con motivo, ver `design.md`): contratos de API, autenticación/autorización,
seguridad de API, E2E por HTTP, performance/load y transiciones de estado de `Change`.

## Capacidades

### Nuevas capacidades

(ninguna - calidad y tooling sin cambio de comportamiento observable)

### Capacidades modificadas

(ninguna - ver `skip_specs`)

## Impacto

- `backend/tests/` (reorganización y tests nuevos), `backend/pyproject.toml` (cobertura de
  ramas, marcadores, configuración de mutmut, `mutmut` como dependencia de desarrollo),
  `justfile` (`test-unit`, `test-integration`, `coverage`, `mutation`),
  `.github/workflows/ci.yml` (pasos separados y umbrales) y un workflow nuevo
  programado/manual de mutación, `docs/testing.md`, `CONTRIBUTING.md`.
- Es posible que algún test nuevo destape un defecto real (como ya ocurrió con el sondeo de
  límites); en ese caso se corrige el código dentro de este change y, si cambia el
  comportamiento observable, se documenta en un delta de specs.
- Done-when: puntuación de mutación ≥ umbral fijado tras medir, cobertura por encima de los
  umbrales, la suite unitaria corre en pocos segundos sin Docker, y `docs/testing.md`
  explica cada punto del checklist.
