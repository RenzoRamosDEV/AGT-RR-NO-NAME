# Tasks

## 1. Reorganización en capas unit / integration

- [x] 1.1 Mover con `git mv` los tests a `tests/unit/{domain,application,adapters,
      entrypoints,fakes}` y `tests/integration/{persistence,workflows}`; los fixtures de
      testcontainers (`database_url`, `engine`, `session_factory`, `create_project`) pasan a
      `tests/integration/conftest.py`; `tests/conftest.py` solo registra el perfil de
      hypothesis y aplica los marcadores `unit`/`integration` por ruta (y declara
      `regression`); verificar que los 96 tests siguen pasando y que `pytest tests/unit` corre
      sin Docker en pocos segundos.
- [x] 1.2 Recetas `just test-unit`, `just test-integration` y `just test` (todo); verificar
      que cada una funciona y que `test-unit` no necesita `DOCKER_HOST`.

## 2. Lógica y requisitos (unit)

- [x] 2.1 Tests de propagación de campos de `Change.new`, `Review.succeeded/failed`,
      `ingest_change` y `record_review_success/failure` (cada campo de entrada acaba en la
      entidad y en el evento; los ids son únicos por llamada); verificar con la medición de
      mutación (tarea 4) que los supervivientes de reenvío desaparecen.
- [x] 2.2 Tabla de decisión de `run_review` llamando a la activity directamente con fakes:
      las 8 combinaciones (agente conocido × change existente × el agente lanza) con su
      resultado esperado y la precedencia (agente desconocido antes que change inexistente);
      verificar que cubre la rama "el change no existe" y que los errores de configuración
      son `non_retryable`.
- [x] 2.3 Invariantes de estado de `Review`: los constructores producen solo combinaciones
      coherentes (completed ⇒ sin error; failed ⇒ sin resumen/score/findings), las entidades
      son inmutables (`FrozenInstanceError`) y los enums rechazan valores desconocidos;
      verificar que quitar `frozen=True` hace fallar el test.

## 3. Property-based (hypothesis)

- [x] 3.1 Propiedades de `Change.new`/`Review` (entradas válidas preservan los campos y
      las inválidas lanzan `ValueError`), round-trip JSON de los payloads de eventos y ley de
      idempotencia de `FakeChangeRepository`/`FakeReviewRepository` (n ingestas con claves
      aleatorias ⇒ tantos cambios como claves distintas, mismo id por clave); perfil `ci`
      determinista.

## 4. Mutation testing

- [x] 4.1 Añadir `mutmut` como dependencia de desarrollo, configurar `[tool.mutmut]` para
      `domain/` y `application/` con los tests de `tests/unit/domain` y `tests/unit/application`,
      receta `just mutation` y un script que lea las estadísticas y falle bajo el umbral;
      verificar que corre en pocos segundos y reproduce la línea base (~206 mutantes).
- [x] 4.2 Revisar los supervivientes: matar los reales con tests y documentar los
      equivalentes; fijar el umbral con el resultado medido; verificar que la puntuación sube
      por encima del ~71 % de partida.

## 5. Persistencia, transacciones y esquema (integration)

- [x] 5.1 Consultas: `ChangeRepository.get()` contra Postgres (existente, inexistente,
      tras reingesta) y lectura de una `Review` con `findings` no vacíos (round-trip por JSONB,
      incluido el camino de conflicto); verificar con testcontainers.
- [x] 5.2 Orden del outbox: los eventos de un proyecto salen con ids crecientes en el orden
      causal (`change.created` antes que `review.*`); verificar con un test.
- [x] 5.3 Rollback de la review: si falla la escritura del evento no queda la `Review`
      (misma garantía que ya tiene el change); verificar con un evento de proyecto inexistente.
- [x] 5.4 Esquema: `upgrade head` + `compare_metadata` contra los modelos no produce
      diferencias, y `upgrade → downgrade base → upgrade` es reversible; corregir modelos o
      migración si el test destapa deriva.

## 6. Concurrencia (integration)

- [x] 6.1 Ingestas simultáneas de la misma clave natural (N sesiones independientes): una fila,
      un evento `change.created`, todas devuelven el mismo id; mismo test para
      `record_review` sobre la misma `(change, agent, run)`; verificar que es estable al
      repetirlo varias veces.
- [x] 6.2 Ráfaga de claves distintas en paralelo: ningún error (sin interbloqueos) y un
      change y un evento por clave.

## 7. Recuperación (integration, Temporal)

- [x] 7.1 Con el worker `agents` ausente el workflow permanece en curso y termina con las
      dos reviews cuando el worker aparece; verificar el estado intermedio (sin reviews) y el
      final.
- [x] 7.2 Fallo transitorio de persistencia dentro de `run_review`: la activity se reintenta y
      queda una única review `completed`.
- [x] 7.3 Acuse perdido tras confirmar: el repositorio de prueba inserta de verdad y luego
      lanza una vez; tras el reintento sigue habiendo una review y un evento.

## 8. Regresión

- [x] 8.1 Un test marcado `regression` por cada defecto ya corregido, con el origen en el
      docstring: agente desconocido sin reintentos, el diff no viaja por Temporal (un diff de
      5 MB atraviesa el workflow y el payload de `RunReviewInput` no lo contiene), `run` se
      propaga, y los valores guardados de `status` son estables (`pending`/`completed`/
      `failed`); verificar con `pytest -m regression`.

## 9. Cobertura de ramas y CI

- [x] 9.1 Activar `--cov-branch`, medir y fijar `fail_under` global y el umbral estricto de
      `domain/`+`application/` (`coverage report --include=... --fail-under`); verificar que
      un test borrado hace fallar el umbral.
- [ ] 9.2 `ci.yml`: pasos separados (unit, integration, umbrales) con
      `HYPOTHESIS_PROFILE=ci`, y workflow nuevo `mutation.yml` programado (semanal) y manual
      con acciones fijadas por SHA; verificar con `actionlint` y una ejecución real
      (`workflow_dispatch`).

## 10. Documentación y siguiente change

- [ ] 10.1 `docs/testing.md`: mapa de cada punto del checklist (cubierto / añadido /
      diferido con motivo), qué test va en qué capa, cómo ejecutar cada receta; enlazar desde
      `CONTRIBUTING.md` y `docs/architecture.md`.
- [ ] 10.2 Añadir a `tasks.md` de `expose-commit-ingestion` los tests que dependen de la API
      (contratos con schemathesis y snapshot de OpenAPI, autenticación y autorización,
      seguridad de API, E2E por HTTP, carga de `POST /ingest/commit`); verificar con
      `openspec validate expose-commit-ingestion --strict`.

## 11. Contraste con Codex y cierre

- [ ] 11.1 Pedir a Codex una revisión de la estrategia y de los tests nuevos (huecos,
      asserts débiles, tests de relleno, flakiness); verificar cada hallazgo contra el código
      antes de aceptarlo y corregir lo que sea cierto.
- [ ] 11.2 Si algún test destapó un defecto real, corregir el código y dejar constancia (delta
      de specs si cambia comportamiento observable); repetir la medición de mutación.
- [ ] 11.3 Verificación final: `just ci`, mutación sobre el umbral y CI real de GitHub en verde.

## Workflow follow-up

- Archivar con `openspec archive strengthen-test-suite --yes` tras mergear (sin specs que
  fundir: `skip_specs`).
