# Tasks

## 1. Estado agregado y resumen de findings

- [x] 1.1 `domain/review_status.py`: `ChangeReviewStatus`, `review_status_from_counts` y
      `normalize_severity`; verificar con tests de tabla de decisión (contadores × esperados),
      valores límite, propiedad "el estado es una función de los contadores" y sinónimos de
      severidad.
- [x] 1.2 `ChangeSummary.review_status`, `ChangeDetail` con `findings_summary` (caso de uso
      `summarize_findings` solo sobre el `run` actual) y `get_change_detail` con
      `expected_agents`; verificar con tests de aplicación (runs anteriores no cuentan, sin
      findings, severidad desconocida).

## 2. Filtros del canal

- [x] 2.1 Puerto `list_for_project(status, q, expected_agents)` y adaptador SQL (contadores del
      run actual, predicado de estado, `icontains` con autoescape); verificar con integración
      sobre Postgres real: paridad SQL/dominio sobre la matriz de contadores, comodines
      literales, combinación con `kind` y cursor, y que el listado sigue sin seleccionar `diff`.
- [x] 2.2 Router: `status` repetible y `q` (recorte, NUL y longitud → 422) y campo
      `review_status` en los schemas; verificar con tests de API y fakes.

## 3. Reintento

- [x] 3.1 `ChangeRepository.advance_run` (compare-and-swap) y workflow id con sufijo `-r{run}`
      para `run > 1` en el starter; verificar con integración (CAS concurrente: solo una
      gana) y con el starter sobre Temporal de test (run 1 conserva el id, run 2 arranca otra
      ejecución).
- [x] 3.2 Caso de uso `retry_review` y `POST /changes/{id}/retry` (token, 202/404/409/503);
      verificar con tests de aplicación y de API, incluidas dos peticiones simultáneas y el
      fallo del starter sin avanzar `run`.

## 4. Salud de dependencias

- [x] 4.1 `GET /health/dependencies` (latencia, `reason` cerrado, sin detalles); verificar con
      tests de API: todo ok, una caída con credenciales en el error, timeout.

## 5. Contrato y cierre

- [x] 5.1 Cablear `composition.py` y `tests/fakes/api.py`; ampliar el E2E de lectura con
      `status`, `q`, un reintento y `/health/dependencies`.
- [x] 5.2 Regenerar `docs/openapi.json` (`just openapi`), actualizar `docs/architecture.md` y
      `docs/testing.md`, y verificar `just lint`, `just test` y `just mutation` en verde.
