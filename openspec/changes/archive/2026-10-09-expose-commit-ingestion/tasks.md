# Tasks

## 1. Configuración

- [x] 1.1 Añadir `pydantic-settings` y crear `config.py` con `Settings` (`DATABASE_URL`,
      `TEMPORAL_ADDRESS`, `INGEST_TOKEN` obligatorio, `MAX_DIFF_CHARS`, `AGENT_NAMES`);
      verificar con tests unitarios: valores por defecto, lectura desde entorno, y que
      falta de `INGEST_TOKEN` lanza error de validación.

## 2. Proyectos (lectura)

- [x] 2.1 Crear `domain/project.py` (`Project`: id, slug), puerto `ProjectRepository`
      (`get_by_slug`) en `application/ports.py` y `FakeProjectRepository` en `tests/fakes/`;
      verificar con `uv run mypy` y `lint-imports`.
- [x] 2.2 Implementar `SqlAlchemyProjectRepository` en
      `adapters/persistence/project_repository.py`; verificar con un test de integración
      (testcontainers) que devuelve el proyecto existente y `None` para un slug inexistente.

## 3. Caso de uso `ingest_commit`

- [x] 3.1 Definir el puerto `ReviewStarter` (`async def start(change: Change) -> None`) y
      mover `ReviewCommitInput` a `application/` (reexportado desde `workflows/dto.py`);
      verificar que la suite existente de `tests/workflows/` sigue en verde.
- [x] 3.2 Implementar `application/ingest_commit.py`: resuelve el proyecto por slug
      (`ProjectNotFound` si no existe), recorta el diff a `max_diff_chars` marcando
      `diff_truncated`, llama a `ingest_change` y luego a `ReviewStarter.start`; verificar
      con tests contra fakes de los cinco requisitos de `commit-ingestion` (salvo auth, que
      es de la API): proyecto desconocido sin efectos, recorte, reingesta idempotente que
      arranca la review una sola vez por commit, y que un fallo del starter deja el
      `Change` persistido.

## 4. Adaptador de Temporal

- [x] 4.1 Implementar `adapters/orchestration/temporal_review_starter.py`: arranca
      `"ReviewCommitWorkflow"` con id `commit-{project_id}-{head_sha}` y trata
      `WorkflowAlreadyStartedError` como éxito; verificar con un test sobre
      `WorkflowEnvironment.start_time_skipping()` que arrancar dos veces el mismo commit
      deja una sola ejecución y no lanza error.

## 5. API HTTP

- [x] 5.1 Schemas Pydantic (`IngestCommitRequest`, `IngestCommitResponse`), dependencia de
      autenticación (`X-Ingest-Token`, `hmac.compare_digest`) y router `POST /ingest/commit`
      (202/401/404); verificar con tests de API (ASGI + fakes) que cubren los requisitos de
      `commit-ingestion`: token ausente, token incorrecto, 404, 202 con `change_id`,
      reingesta con el mismo `change_id`, y diff recortado.
- [x] 5.2 `create_app(settings)` con `lifespan` que construye engine, `session_factory`,
      repositorios, cliente de Temporal perezoso y `TemporalReviewStarter`, y los libera al
      cerrar; los tests de API sustituyen las dependencias sin tocar variables de entorno;
      verificar que `/health` sigue respondiendo sin base de datos ni Temporal.
- [x] 5.3 `GET /ready`: comprueba Postgres (`SELECT 1`) y Temporal; 200 / 503 indicando la
      dependencia que falla; verificar con los tres escenarios del delta de `service-health`
      usando comprobadores falsos, y con Postgres real (testcontainers) para el caso feliz.

## 6. Worker de desarrollo

- [x] 6.1 `review_arena/worker.py` (raíz de composición, ver design): un solo proceso que registra `ReviewChangeWorkflow` y
      `ReviewCommitWorkflow` en `platform` y `run_review` en `agents` con `FakeAgent` por
      cada nombre de `AGENT_NAMES`, más la receta `just worker`; verificar que arranca y
      se conecta a un Temporal de test (smoke test) y que `lint-imports` sigue limpio.

## 7. Verificación vertical y manual

- [x] 7.1 Test vertical: app ASGI real + Postgres (testcontainers) + Temporal time-skipping
      con los workers de la tarea 6.1; `POST /ingest/commit` termina con dos `Review`
      `completed` persistidas y reenviarlo no crea una tercera; verificar con
      `uv run pytest backend/tests/e2e -q`.
- [x] 7.2 Verificación manual contra Temporal real: `just dev`, `just worker`,
      `INSERT` de un proyecto, `curl` al endpoint, y comprobar en la Temporal Web UI y con
      SQL directo que hay dos `Review`; documentar los pasos en `README.md` y enlazar las
      capacidades nuevas en `docs/architecture.md`.
- [x] 7.3 Verificación final: `just ci` en verde y CI real de GitHub en verde.

## 8. Tests que dependen de la API (heredados de `strengthen-test-suite`)

Estos tipos de test no se pudieron escribir antes porque no existía el endpoint
(ver `docs/testing.md`). Entran con el código que prueban, no después.

- [x] 8.1 Contratos: snapshot del OpenAPI generado (`docs/openapi.json`) con un test que falla
      si cambia sin actualizarlo, y `schemathesis` ejecutado contra la app ASGI (contrato +
      fuzzing de entradas); verificar que una respuesta fuera de contrato rompe el test.
- [x] 8.2 Autenticación y autorización: token ausente, vacío, con espacios, con distinta
      capitalización y de longitud distinta → siempre 401 sin efectos; `/health` y `/ready`
      no exigen token y `POST /ingest/commit` sí; comprobar que se usa comparación en tiempo
      constante (espía sobre `hmac.compare_digest`).
- [x] 8.3 Seguridad de la API: cuerpo malformado o con tipos erróneos → 422 sin traza,
      payloads hostiles (SQL, NUL, Unicode raro, campos por encima de los límites de
      `harden-input-limits`) → rechazo o persistencia segura, y que ni el token ni trazas
      internas aparecen en respuestas de error ni en logs.
- [x] 8.4 E2E de flujos críticos por HTTP: el test vertical de la tarea 7.1 cubre el camino
      feliz; añadir los críticos restantes (reingesta idempotente, Temporal caído → 503 y
      reenvío posterior que arranca la review, proyecto inexistente).
- [x] 8.5 Carga: prueba de carga ligera sobre `POST /ingest/commit` (script `httpx` asíncrono,
      sin dependencias nuevas en vez de Locust o k6) con
      presupuesto explícito (p95 de latencia y 0 errores a la concurrencia esperada de un
      uso personal), ejecutable bajo demanda y no en cada push; documentar el presupuesto y
      el resultado de la primera medición en `docs/testing.md`.

## Workflow follow-up

- Archivar con `openspec archive expose-commit-ingestion --yes` tras mergear, para que
  `commit-ingestion` pase a ser spec activo y el delta de `service-health` se funda.
- Registrar como ADR la decisión de token estático (y su reemplazo previsto) cuando se
  aborde el slice de `Project`.
