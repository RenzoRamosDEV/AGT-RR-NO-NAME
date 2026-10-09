# Tasks

## 1. Resumen del diff

- [x] 1.1 `domain/diff.py` (`summarize_diff`, `DiffSummary`) y `Change.diff_summary` calculado en
      `Change.new`; verificar con tests de dominio (dos archivos, cabeceras `---`/`+++`, líneas
      que empiezan por `++`/`--`, sin formato git, límite de 200 archivos) y propiedad (suma de
      archivos = totales, el resumen no depende del orden de las líneas de contexto).
- [x] 1.2 Migración `changes.diff_summary` con relleno por lotes y adaptador (guardar/leer, listado
      sin `diff`); verificar con integración: migración sobre datos existentes igual a
      `summarize_diff`, el listado no selecciona `diff` y el detalle devuelve el resumen.
- [x] 1.3 `diff_summary` en los schemas de listado y detalle; verificar con tests de API.

## 2. Estadísticas por proyecto

- [x] 2.1 `ReviewRepository.agent_stats(project_id)`, caso de uso con `ProjectNotFound` y
      `?project=` en el router (NUL/longitud → 422); verificar con tests de aplicación y API, y
      con integración sobre Postgres (dos proyectos con el mismo agente).

## 3. `created` en la ingesta

- [x] 3.1 `Change.new(id=...)`, `IngestResult` y `created` en las respuestas de commit y PR;
      verificar con tests de aplicación (nuevo, repetido, PR vs commit) y de API (202 en ambos).

## 4. Eventos de un change

- [x] 4.1 Puerto `ChangeEventRepository`, adaptador SQL con índice de expresión, caso de uso con
      lista blanca y `GET /changes/{id}/events`; verificar con tests de aplicación (tipos
      desconocidos, `error` omitido), de API (404) e integración (orden y aislamiento por change).

## 5. Salida cruda para el operador

- [x] 5.1 `Settings.operator_token` (distinto del de ingesta, mínimo 16), `require_operator_token`,
      `ReviewRepository.get` y `GET /reviews/{id}/raw-output`; verificar con tests de
      configuración, de API (deshabilitado, 401, el token de ingesta no vale, 404, `no-store`) y
      que el detalle público sigue sin `raw_output`.

## 6. Contrato y cierre

- [x] 6.1 Cablear `composition.py` y `tests/fakes/api.py`; ampliar el E2E de lectura.
- [x] 6.2 Regenerar `docs/openapi.json` (`just openapi`), actualizar `docs/architecture.md` y
      `docs/testing.md`, y verificar `just lint`, `just test` y `just mutation` en verde.
