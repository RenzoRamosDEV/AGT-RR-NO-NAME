# Tasks

## 1. Dominio puro

- [x] 1.1 Crear `domain/change.py` con la entidad `Change` (id, project_id, kind, ref,
      head_sha, title, author, url, diff, diff_truncated, status, run, created_at) y el VO
      `ChangeKind` (`commit` | `pr`); sin imports de `application`, `adapters` ni librerías
      externas de infraestructura; verificar con `uv run lint-imports` y un test unitario
      que construye un `Change` válido y uno que rechaza un `ChangeKind` inválido.
- [x] 1.2 Modelar el evento de dominio `ChangeCreated` (tipo + payload mínimo: change_id,
      project_id, kind, head_sha) como dataclass simple en `domain/events.py`; verificar
      con un test que serializa su payload a dict sin perder campos.

## 2. Puerto y caso de uso (con repositorio falso)

- [x] 2.1 Definir el puerto `ChangeRepository` en `application/ports.py` (`Protocol`) con
      `async def add(self, change: Change, event: ChangeCreated) -> Change` (devuelve el
      `Change` persistido o el existente si ya estaba, ver tarea 2.3); verificar que
      `application/` sigue sin importar SQLAlchemy (`uv run lint-imports`).
- [x] 2.2 Implementar `FakeChangeRepository` en `backend/tests/fakes/` (diccionario en
      memoria, sin Postgres) para usar en los tests del caso de uso; verificar que cumple
      el `Protocol` (`uv run mypy` no debe quejarse al pasarlo donde se espera
      `ChangeRepository`).
- [x] 2.3 Implementar el caso de uso `ingest_change` en `application/ingest_change.py`;
      verificar con tests contra `FakeChangeRepository` que cubren los dos requirements del
      spec: ingesta exitosa crea `change` + evento, y reingestar el mismo
      `(project_id, kind, head_sha)` es idempotente (no crea un segundo evento) - correr con
      `uv run pytest backend/tests/application/test_ingest_change.py -q`.

## 3. Esquema y migración

- [ ] 3.1 Configurar Alembic en `backend/alembic/` (`alembic init` + `env.py` apuntando a
      `DATABASE_URL` vía variable de entorno) y añadir `alembic` + `sqlalchemy[asyncio]` +
      `asyncpg` a `backend/pyproject.toml`; verificar con `uv run alembic current` sin
      errores contra una base vacía.
- [ ] 3.2 Escribir la migración inicial: tablas `projects` (id, slug mínimo), `changes`
      (con `UNIQUE (project_id, kind, head_sha)`), `events` (id bigserial, project_id,
      type, payload jsonb, created_at); verificar con `uv run alembic upgrade head` seguido
      de `uv run alembic downgrade base` sin errores (migración reversible).

## 4. Adaptador SQLAlchemy

- [ ] 4.1 Crear los modelos SQLAlchemy 2.0 async en `adapters/persistence/models.py`
      (mapeados a las tablas de la tarea 3.2) y el engine/sesión async en
      `adapters/persistence/db.py`; verificar que `adapters/` es el único paquete que
      importa `sqlalchemy` (`uv run lint-imports`).
- [ ] 4.2 Implementar `SqlAlchemyChangeRepository.add()`: inserta `change` + `event` en una
      sola transacción; si la constraint `UNIQUE` salta, captura la violación, recupera el
      `Change` existente dentro de la misma transacción y lo devuelve sin insertar un
      segundo evento (documentar en un comentario qué excepción de `asyncpg` se captura y
      por qué, según `design.md - Decisions`); verificar con un test unitario que mockea la
      sesión para el camino de violación de unicidad.

## 5. Verificación de integración (testcontainers)

- [ ] 5.1 Escribir el test de integración en
      `backend/tests/adapters/test_sqlalchemy_change_repository.py` usando
      `testcontainers[postgres]`: levanta un Postgres real, aplica las migraciones de
      Alembic, y verifica los dos escenarios del spec `change-ingestion` (persistencia
      atómica del change+evento, e idempotencia por `(project_id, kind, head_sha)` incluso
      para dos proyectos distintos con el mismo `head_sha`); verificar con
      `uv run pytest backend/tests/adapters/ -q` (requiere Docker/Podman local).
- [ ] 5.2 Añadir el job (o pasos) de testcontainers al `backend-test` de
      `.github/workflows/ci.yml` (el runner de GitHub Actions trae Docker, no hace falta
      Podman ahí); verificar abriendo una PR y confirmando que el test de integración corre
      y pasa en el CI real, no solo en local.

## 6. Cierre de la fase

- [ ] 6.1 Actualizar `docs/architecture.md` con un enlace a este change una vez archivado,
      y confirmar que `just test` (ahora incluyendo los tests nuevos) sigue en verde de
      punta a punta; verificar con `just ci`.

## Workflow follow-up

- Archivar este change con `openspec archive add-change-ingestion` una vez mergeado, para
  que `change-ingestion` pase a ser spec activo junto a `service-health`.
- Verificar tras el archive que `openspec list --specs` muestra ambas capacidades.
