# Tasks

## 1. NUL en `project`

- [x] 1.1 Rechazar NUL en `IngestCommitRequest.project` y devolver `None` desde
      `SqlAlchemyProjectRepository.get_by_slug` ante un slug con NUL; verificar con un test
      de API (422 sin efectos, junto a los demás límites) y uno de integración con Postgres
      real (`None`, sin excepción).

## 2. Política de reutilización del workflow id

- [x] 2.1 Arrancar con `ALLOW_DUPLICATE_FAILED_ONLY`; verificar con tests de integración
      sobre Temporal de test: tras completar el workflow, `start()` no cambia el `run_id`; tras
      terminar en fallo, `start()` crea una nueva ejecución.

## 3. Verificación

- [x] 3.1 `just ci` y `just mutation` en verde, `docs/openapi.json` sin cambios (o regenerado
      si el schema cambia) y CI de GitHub en verde; archivar el change.
