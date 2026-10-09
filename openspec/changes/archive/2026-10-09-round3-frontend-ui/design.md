# Design

## Context

El detalle de un change pinta el diff como una tabla numerada (`parseDiff`), las estadísticas son
una tabla estática y las tarjetas del canal no muestran fecha. El backend ya devuelve
`created_at` en el listado y el detalle (`round1-backend-api`). Se mantiene el tema negro
(ADR 0002), el contraste AA y `prefers-reduced-motion`.

## Goals / Non-Goals

**Goals:** cinco mejoras de uso diario con la lógica en funciones puras de `lib/` y testeables.

**Non-Goals:** estadísticas reales por API, ordenar en servidor, persistir la vista elegida,
diff en columnas lado a lado, tokens reales en el estado vacío.

## Decisions

- **Archivos del diff (`parseDiff` + `diffFiles`).** `parseDiff` sigue devolviendo filas planas,
  pero ahora también `file` (cabecera de archivo) en cada fila de tipo `header`. Se aceptan tres
  formas: `@@ <archivo>` (formato de ejemplo), `diff --git a/x b/x` + `---`/`+++`/`index`
  (git), y `@@ -a,b +c,d @@` (hunk dentro del archivo actual). Las líneas `diff --git`, `index`,
  `---` y `+++` son metadatos: se muestran como cabecera y no cuentan como `del`/`add`
  (hoy `--- a/x` se contaría como borrada). `diffFiles` agrupa por archivo y cuenta `+`/`-`;
  sin ninguna cabecera hay un único archivo «(sin nombre)». Cada fila de cabecera de archivo
  lleva un `id` de ancla (`diff-file-N`) y el navegador enlaza con `href="#…"` (salto nativo,
  accesible por teclado y sin estado).
- **Ordenación (`lib/sort.ts`).** `sortRows(rows, key, direction)` es genérica, estable y no muta;
  los números se comparan como números y el resto con `localeCompare`. La cabecera activa lleva
  `aria-sort` y es un `<button>` dentro del `<th>`; pulsar de nuevo invierte el sentido. Orden
  inicial: el del origen, sin `aria-sort`.
- **Antigüedad (`lib/relativeTime.ts`).** `relativeTime(iso, now)` recibe el instante actual (no
  llama a `Date.now()`), así los tests son deterministas. Escalas: «hace un momento» (<1 min),
  minutos, horas, días; más de 30 días muestra la fecha. Una fecha futura o no válida se trata
  como «hace un momento» o se omite, respectivamente. La UI usa `<time dateTime title>` y un
  `NowProvider` mínimo (contexto con `Date` inyectable) refrescado cada minuto.
- **`createdAt` opcional en `Change`.** `toChange` lo mapea desde `created_at`; los datos de
  ejemplo lo traen calculado respecto a un instante fijo. Si falta, no se pinta fecha.
- **Vista compacta.** Un interruptor `aria-pressed` («Tarjetas» / «Compacta») en la barra del canal
  cambia un `data-density` del contenedor; la compacta es una fila por change (tipo, título,
  autor, SHA, fecha y resumen) con el hilo de respuestas disponible igualmente. Es estado local de
  la página: no se persiste.
- **Estado vacío accionable (`lib/ingestHint.ts`).** Con cero changes y sin filtros activos, el
  canal muestra un comando `curl` para `POST /ingest/commit` con el `project` del canal y el
  placeholder `$INGEST_TOKEN`; la URL base sale de `VITE_API_URL` (o `http://localhost:8000`).
  Nunca se pinta un token real. El comando se puede copiar con `CopyButton`.

## Risks / Trade-offs

- El parser de diff es heurístico: un contenido que empiece por `--- ` o `+++ ` dentro de un
  hunk se tomaría como metadato. Solo se reconocen dentro de una cabecera `diff --git`, antes del
  primer hunk, para acotar el riesgo.
- El reloj de «hace X» se actualiza por minuto: no es en tiempo real exacto, pero evita
  re-renderizados constantes.
- Sin API de proyectos vacíos distinta, el estado vacío también se ve en un proyecto recién
  creado antes de ingestar nada: es justo el caso buscado.
