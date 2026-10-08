# Tasks

## 1. Dominio puro

- [x] 1.1 Crear `domain/review.py`: VO `Finding` (severity, file, line, message),
      `ReviewResult` (summary, score, findings) y la entidad `Review` (id, change_id,
      agent, run, status, summary, score, findings, raw_output, duration_ms, error,
      created_at); verificar con `uv run lint-imports` y un test unitario que construye
      una `Review` exitosa y una fallida.
- [x] 1.2 Modelar los eventos `ReviewCompleted` y `ReviewFailed` en `domain/events.py`
      (mismo patrón que `ChangeCreated`); verificar con un test que cada uno serializa su
      payload sin perder campos.

## 2. Puertos y caso de uso (con fakes)

- [x] 2.1 Definir el puerto `ReviewAgent` en `application/ports.py`
      (`async def review(self, change: Change) -> ReviewResult`); implementar `FakeAgent`
      en `adapters/agents/fake.py` (constructor recibe `name: str`, devuelve un
      `ReviewResult` fijo o configurable para simular fallo); verificar con un test que
      dos instancias de `FakeAgent` con nombres distintos son independientes.
- [x] 2.2 Definir el puerto `ReviewRepository` en `application/ports.py`
      (`async def add(self, review: Review) -> Review`, idempotente por
      `(change_id, agent, run)`, mismo patrón que `ChangeRepository.add`); implementar
      `FakeReviewRepository` en `backend/tests/fakes/`; verificar que cumple el
      `Protocol` (`uv run mypy`).
- [x] 2.3 Implementar el caso de uso `record_review` en `application/record_review.py`;
      verificar con tests contra los fakes que cubren los tres requirements del spec
      `change-review`: dos reviews por change, idempotencia por natural key, y que
      registrar un fallo no lanza excepción (se persiste como `Review` con estado de
      fallo).

## 3. Ampliar ChangeRepository con lectura

- [x] 3.1 Añadir `get(self, change_id: UUID) -> Change | None` al puerto
      `ChangeRepository` en `application/ports.py`; actualizar `FakeChangeRepository`
      (tarea ya completada en `add-change-ingestion`) para implementarlo; verificar con
      un test que devuelve `None` para un id inexistente y el `Change` correcto para uno
      existente.
- [x] 3.2 Implementar `get()` en `SqlAlchemyChangeRepository`; verificar con un test
      unitario de sesión mockeada (mismo estilo que `add()`).

## 4. Persistencia de reviews

- [x] 4.1 Migración Alembic: tabla `reviews` (id, change_id FK, agent, run, status,
      summary, score, findings jsonb, raw_output, duration_ms, error, created_at) con
      `UNIQUE (change_id, agent, run)`; verificar con `uv run alembic upgrade head` +
      `downgrade base` (reversible) contra Postgres real.
- [x] 4.2 Modelos SQLAlchemy (`ReviewModel`) y `SqlAlchemyReviewRepository.add()` con
      `INSERT ... ON CONFLICT (change_id, agent, run) DO NOTHING RETURNING id` (mismo
      patrón que `SqlAlchemyChangeRepository`, ver `design.md` de `add-change-ingestion`);
      verificar con un test unitario de sesión mockeada para el camino de conflicto.
- [x] 4.3 Test de integración con testcontainers: persistir dos `Review` para el mismo
      `change_id` con agentes distintos, confirmar idempotencia reintentando la misma
      `(change_id, agent, run)`, y confirmar que el evento (`review.completed` /
      `review.failed`) queda en la tabla `events`; verificar con
      `uv run pytest backend/tests/adapters/ -q` (requiere Docker/Podman).

## 5. Workflows de Temporal

- [x] 5.1 Añadir `temporalio` a `backend/pyproject.toml`; crear
      `workflows/review_change.py` con `ReviewChangeWorkflow`: una activity
      `run_review(change_id, agent_name, run)` en `task_queue="agents"` que carga el
      `Change` (vía `ChangeRepository.get`, en una activity de `task_queue="platform"`
      separada) y ejecuta `FakeAgent.review()` + `record_review`, lanzada dos veces en
      paralelo (`asyncio.gather`) para dos agentes distintos; verificar que el código del
      workflow no hace I/O directo (todo vive en activities) revisando el diff a mano.
- [x] 5.2 Crear `workflows/review_commit.py` con `ReviewCommitWorkflow` (ID determinista
      `commit-{project_id}-{sha}` o equivalente con lo disponible hoy) que arranca
      `ReviewChangeWorkflow` como hijo una vez; verificar con un test que arrancarlo dos
      veces con el mismo ID no duplica el workflow (comportamiento nativo de Temporal por
      `workflow_id` repetido).

## 6. Verificación con Temporal time-skipping

- [x] 6.1 Test con `WorkflowEnvironment.start_time_skipping()`: arrancar
      `ReviewChangeWorkflow` para un `change_id` persistido de antemano (con fakes o
      contra Postgres real, decidir según velocidad) y confirmar que produce dos
      `Review`; verificar con `uv run pytest backend/tests/workflows/ -q`.
- [x] 6.2 Test de fallo parcial: un `FakeAgent` configurado para fallar, confirmar que la
      `Review` del otro agente igual queda persistida y que el workflow no se cae entero;
      verificar en el mismo archivo de tests que la tarea 6.1.
- [x] 6.3 Verificación manual contra Temporal real: `just dev` (ya incluye Temporal +
      Temporal UI desde Fase 0), arrancar `ReviewCommitWorkflow` a mano (script o REPL) y
      confirmar en la Temporal Web UI (`localhost:8080`) que el workflow corrió y las dos
      `Review` quedaron en Postgres; verificar con una consulta SQL directa.

## Workflow follow-up

- Archivar este change con `openspec archive add-review-workflow` una vez mergeado, para
  que `change-review` pase a ser spec activo y el delta de `change-ingestion` (el
  requisito de `get()`) se funda en su spec principal.
- Verificar tras el archive que `openspec list --specs` muestra `change-review`,
  `change-ingestion` y `service-health`.
