# Design

## Reviews ligeras en el listado (E)

Se descartó añadir un agregado JSON `LATERAL` a la consulta del canal: esa consulta ya usa un
`LATERAL` de contadores que Postgres evalúa por change en el orden del índice, y meterle además
`json_agg` complicaba el plan y los tests de paridad con `review_status`. En su lugar el repositorio
hace **una segunda consulta por página**: `reviews JOIN changes` filtrada por
`changes.id IN (ids de la página)` y `reviews.run = changes.run`, que recorre el índice
`(change_id, run, status)`. Son dos consultas con independencia del tamaño de la página (sin N+1) y
solo se seleccionan columnas ligeras: ni `summary`, ni `findings`, ni `error`, ni `raw_output`.

- `ReviewBrief` (modelo de lectura) y `ReviewBriefResponse` (API) llevan `agent`, `status`, `score`,
  `duration_ms` y `run`.
- `ChangeListItemResponse` extiende el resumen del change con `reviews`; el detalle sigue
  devolviendo las reviews completas (`ReviewResponse`) en el mismo campo `reviews`, así que el
  frontend distingue ambas por la marca `partial` que él mismo pone al mapear el listado.
- Ordenadas por agente para que el resultado sea estable.

## Agentes configurados (I)

`agent_names` viaja en `GET /health/dependencies` (aditivo) en vez de un endpoint nuevo: el
frontend ya lo consulta en Ajustes y no añade superficie. `ApiDependencies.agent_names` lo rellena
la composición desde `Settings.agent_names`; los fakes de tests lo toman de su `Settings`.

En el frontend el hook `useAgentNames()` pide el diagnóstico una vez por página; mientras se
desconoce (carga o fallo) el texto dice «los agentes configurados» y **no** asume ninguno. El estado
agregado de los datos de ejemplo usa el número de agentes de su propio diagnóstico en lugar de una
constante.

## Detalle por runs (D)

`splitRuns(reviews, run)` separa las del run actual (las sin `run` cuentan como 1, igual que el
valor por defecto del backend) de las anteriores, agrupadas por run y de la más reciente a la más
antigua. Los hallazgos y las cards principales usan solo el run actual; las anteriores van en
`<details>` colapsados (accesibles con teclado, sin JS propio).

## Detalle completo bajo demanda en el canal

`useFullReviews` pide `GET /changes/{id}` cuando se abre «Ver respuestas» y alguna review es
`partial`. Muestra las ligeras mientras carga, un aviso con «Reintentar» si falla y vuelve a pedir
el detalle si cambia el `run` o el estado agregado con el hilo abierto (el sondeo del canal lo
actualiza). Sin reviews, el resumen del card conserva el badge del estado agregado
(`Pendiente`, etc.) en lugar de quedarse vacío.
