# Tasks

## 1. Ingesta de PRs

- [x] 1.1 Generalizar `ingest_commit` a `ChangeSubmission` + `ingest_pr`, y hacer que el
      starter de Temporal use `{kind}-{project_id}-{head_sha}`; verificar con tests de
      aplicación (kind `pr`, idempotencia, proyecto desconocido sin efectos, fallo del starter
      conserva el change) y con un test del starter sobre Temporal de test (PR y commit con
      el mismo sha arrancan dos ejecuciones; el id de commit no cambia).
- [x] 1.2 `POST /ingest/pr` (schemas, router con la lógica de errores compartida) y
      `ApiDependencies.ingest_pr`; verificar con tests de API (401, 404, 422, 503, 202,
      reingesta) y que `/ingest/commit` sigue igual.

## 2. Lecturas de proyectos y canal

- [x] 2.1 Read models, puertos (`ProjectRepository.list_all`, `ChangeRepository.list_for_project`)
      y casos de uso `list_projects` / `list_changes` (paginación `limit + 1`); verificar con
      tests contra fakes, incluida la propiedad "recorrer todas las páginas devuelve todos los
      changes, sin repetir y en orden".
- [x] 2.2 Adaptadores SQLAlchemy con keyset sobre `(created_at, id)` y sin cargar el diff;
      verificar con tests de integración (Postgres real): orden, filtro por `kind`, empate de
      `created_at`, cursor, y que la consulta no selecciona `diff`.
- [x] 2.3 Routers `GET /projects` y `GET /projects/{slug:path}/changes` con `kind`, `limit`
      (1-100) y `cursor` (codificación en `entrypoints/api/cursor.py`); verificar con tests de
      API: slug con barra, 404, 422 por cursor/límite inválidos, `next_cursor` solo si hay más.

## 3. Detalle de change y estadísticas

- [x] 3.1 `ReviewRepository.list_for_change` y `agent_stats`, casos de uso `get_change_detail`
      y `agent_stats`; verificar con fakes y con integración (medias que ignoran `NULL`,
      agente solo con fallos, sin reviews).
- [x] 3.2 Routers `GET /changes/{id}` y `GET /stats/agents` (sin `raw_output` en la respuesta);
      verificar con tests de API (404, reviews completada y fallida, lista vacía).

## 4. Composición y contrato

- [x] 4.1 Cablear los nuevos callables en `composition.py` y `tests/fakes/api.py`; verificar
      con un E2E por HTTP (ASGI + Postgres + Temporal de test): ingerir un PR y un commit,
      listar el canal, abrir el detalle y ver las dos reviews, y consultar las estadísticas.
- [x] 4.2 Regenerar `docs/openapi.json` (`just openapi`), actualizar `docs/testing.md` si
      cambia el mapa de tests, y verificar `just lint` y `just test` en verde (cobertura de
      `domain`+`application` al 100 %).
