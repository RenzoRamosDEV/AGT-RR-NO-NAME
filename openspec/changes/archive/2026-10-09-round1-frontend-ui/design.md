# Design

## Context

El frontend usa datos de ejemplo (`data/mock.ts`) hasta que exista la API de lectura. Se respeta
el tema negro único (ADR 0002), el contraste AA y `prefers-reduced-motion`.

## Goals / Non-Goals

**Goals:** cinco mejoras de UI aisladas, con lógica pura testeable en `lib/`.

**Non-Goals:** datos reales, paginación, resaltado de sintaxis, diff lado a lado, gráficos con
librería.

## Decisions

- **Menú móvil solo con CSS + estado React:** el botón existe siempre en el DOM y se oculta con
  CSS por encima de 760 px; el panel se colapsa solo en móvil (`data-open`). Evita duplicar la
  navegación. Se cierra al cambiar de ruta (`useLocation`) y con Escape.
- **Búsqueda local, insensible a mayúsculas, en `lib/search.ts`:** coincide en título, autor y
  SHA (subcadena). Se aplica junto al filtro de tipo.
- **Resumen en `lib/reviewSummary.ts`:** función pura que cuenta por estado y pluraliza el
  texto; se muestra como badges con texto (no solo color).
- **Diff en `lib/diff.ts`:** `parseDiff` devuelve filas `header | add | del | context` con
  numeración antigua/nueva; interpreta cabeceras `@@ -a,b +c,d @@` y, si la cabecera es solo un
  nombre de archivo, reinicia la numeración en 1. Las filas llevan un `id` estable (sin usar el
  texto como key). `Change.truncated` (opcional) activa un aviso `role="note"`.
- **Barras de estadísticas:** `lib/meter.ts` calcula la proporción; la barra es decorativa
  (`aria-hidden`) y el valor sigue en texto dentro de la celda. Sin animaciones, así que no hay
  nada que adaptar a movimiento reducido.

## Risks / Trade-offs

- La numeración de líneas con cabeceras sin rangos es aproximada; con diffs reales de la API
  (Fase 4) llevarán rangos `@@ -a,b +c,d @@`.
- El menú móvil no se puede probar visualmente en jsdom; se prueba el comportamiento
  (aria-expanded, cierre) y no el layout.
