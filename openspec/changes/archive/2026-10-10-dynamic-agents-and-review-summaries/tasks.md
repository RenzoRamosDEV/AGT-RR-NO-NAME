# Tasks

## 1. Backend: reviews ligeras en el canal

- [x] 1.1 `ReviewBrief` en los modelos de lectura y `ChangeSummary.reviews`; el repositorio rellena las del run actual con una segunda consulta por página y solo columnas ligeras
- [x] 1.2 `ReviewBriefResponse` y `ChangeListItemResponse`; `ChangePageResponse.items` las usa; el detalle no cambia
- [x] 1.3 Tests: API (solo campos ligeros, solo run actual, lista vacía) e integración con Postgres real (dos consultas con 5 changes, sin columnas pesadas, sin reviews del run anterior)

## 2. Backend: agentes configurados

- [x] 2.1 `agent_names` en `DependenciesHealthResponse`, `ApiDependencies` y la composición
- [x] 2.2 Test del diagnóstico con nombres personalizados y actualización del test del diagnóstico vacío

## 3. Frontend

- [x] 3.1 `api.ts` mapea las reviews ligeras (`partial`, id derivado) y `agent_names`; el detalle sigue sin `partial`
- [x] 3.2 `useAgentNames` y `agentList`; el canal, el estado vacío y Ajustes usan los agentes reales; `EXPECTED_AGENTS` desaparece
- [x] 3.3 El canal pide el detalle completo al abrir «Ver respuestas» (carga, error con reintento) y conserva el badge agregado sin reviews
- [x] 3.4 El detalle muestra el run actual y deja los anteriores colapsados por run (`splitRuns`)
- [x] 3.5 Tests de regresión con origen: agentes `agent_1,agent_2,gemini`, reviews ligeras y detalle bajo demanda, change con `run = 2`

## 4. Cierre

- [x] 4.1 `docs/openapi.json` regenerado y docs actualizadas
- [x] 4.2 `just ci` en verde (lint, tests con cobertura, build) y mutación en los módulos de backend tocados
