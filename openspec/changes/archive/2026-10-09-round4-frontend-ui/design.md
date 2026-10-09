# Design

## Context

`DataSource` ya abstrae la API real (`createHttpSource`) y los datos de ejemplo
(`createMockSource`). El contrato de lectura viene de `round1-backend-api` y el de `status`, `q`,
`review_status`, reintento y salud de `round2-backend-api` (`design.md` y specs de ese change).
Se mantiene el tema negro (ADR 0002), el contraste AA y `prefers-reduced-motion`.

## Goals / Non-Goals

**Goals:** que cada pantalla use el dato real cuando hay `VITE_API_URL`, que el modo de ejemplo
sea coherente con él (mismos filtros, mismo estado agregado) y que el reintento sea seguro de usar.

**Non-Goals:** autenticación de usuarios, persistir el token (ni en `localStorage` ni en el
build), «% útiles» y versión de prompt en estadísticas (la API no los tiene), edición de ajustes,
refresco automático del diagnóstico.

## Decisions

- **`DataSource` gana tres métodos y un parámetro.** `changes(slug, { kind, status, q, cursor })`
  con `status: ReviewAggregate[]` (repetible en la URL, `?status=a&status=b`); `agentStats()`;
  `health()`; `retry(id, token)`. Los nombres de campo del contrato (`snake_case`) se adaptan en
  `api.ts` al modelo de la UI (`camelCase`).
- **Filtro de estado de la UI → estados del servidor** (`lib/channelQuery.ts`): «En curso» =
  `pending`+`running`, «Con fallos» = `failed`+`partial_failed`, «Completados» = `completed`,
  «Todos» = sin `status` (igual que el diseño del backend). Cambia la semántica antigua
  (cliente, no exclusiva): ahora es la del servidor, una sola fuente de verdad.
- **Búsqueda con retardo.** `useChannel` recibe `q` ya recortado y con un retardo de 300 ms
  (`useDebouncedValue`) para no lanzar una petición por tecla; las respuestas obsoletas se
  descartan (ya lo hace `useAsync`). Cambiar `q`, `kind`, `status` o proyecto genera una primera
  página nueva y descarta el cursor y las páginas extra (están atadas a la primera página).
- **Fuente de ejemplo coherente.** `createMockSource` aplica `kind`, `status` y `q` con las
  mismas reglas que el servidor (subcadena sin mayúsculas en título, autor, SHA y ref) y calcula
  `reviewStatus` con `lib/reviewStatus.ts`, que replica la regla del backend (contadores de
  reviews completadas/fallidas frente a los agentes esperados, 2). El reintento de ejemplo
  mantiene el estado por instancia de fuente (el change vuelve a `pending`, sin reviews) y no
  muta los datos compartidos.
- **`reviewStatus` y `run` en `Change`.** Opcionales: lo trae el listado y el detalle de la API.
  Cuando no hay reviews (listado de la API) la card muestra una insignia con el estado agregado
  en vez del resumen por review.
- **Reintento y token.** El token se escribe en un campo `type="password"` del propio detalle y
  se guarda en un almacén de módulo en memoria (`lib/ingestToken.ts`, `useSyncExternalStore`):
  sobrevive a la navegación dentro de la pestaña y desaparece al recargar. Nunca va a
  `localStorage`, a la URL ni al build. Un 401 lo borra. El botón solo aparece con
  `reviewStatus` `failed` o `partial_failed`. Resultados: 202 → mensaje con el nuevo run y
  recarga del detalle; 401 → «token no válido»; 404 → no encontrado; 409 → «ya no se puede
  reintentar» y recarga (otro lo reintentó o cambió de estado); 503 → «orquestador no
  disponible»; red → error de conexión. Un solo envío a la vez (botón deshabilitado).
- **Estadísticas.** Columnas: Agente, Total, Completadas, Fallos, Duración media, Nota media.
  Los medios nulos (sin datos) se muestran «—» y, al ordenar, los nulos van siempre al final
  (`sortRows`). Las barras decorativas se mantienen en duración y fallos.
- **Diagnóstico.** Ajustes pide proyectos y salud con `useAsync` independientes (un fallo no
  tapa al otro), un botón «Actualizar» recarga la salud y muestra por dependencia estado,
  latencia y motivo (`timeout`/`error`) con vocabulario cerrado traducido; nunca texto libre del
  servidor.
- **Metadatos de review.** `Review` gana `run`, `durationMs`, `score` y `error`. La card muestra
  una lista con «Run N», duración y nota cuando existen, y para las fallidas el error
  **sanitizado** (`lib/sanitize.ts`): sin caracteres de control, espacios colapsados, valores que
  parecen secretos (`token=…`, `sk-…`, `Bearer …`) ocultos y recorte a 200 caracteres. Siempre se
  pinta como texto (React lo escapa).

## Risks / Trade-offs

- Con la API real el filtro de estado depende de `review_status` del servidor; contra un backend
  sin `round2-backend-api` el parámetro se ignoraría y la UI mostraría todo. Es una dependencia
  de despliegue, documentada aquí.
- El almacén de token en módulo es estado global: los tests lo reinician con `clearIngestToken`.
- El retardo de la búsqueda añade 300 ms hasta ver resultados; es el precio de no saturar la API.
- El contrato se ha deducido de los specs y de `schemas.py` del backend en curso y se prueba con
  `fetch` simulado, no contra el backend real.
