# Design

## Context

Las páginas importan `data/mock.ts` de forma síncrona. La API de lectura (`round1-backend-api`)
devuelve: `GET /projects` → `[{id, slug}]`; `GET /projects/{slug}/changes?kind&limit&cursor` →
`{items: ChangeSummary[], next_cursor}` (sin diff ni reviews); `GET /changes/{id}` → change con
`diff` y `reviews[]` (cada una con `findings: [{severity, file, line, message}]`). Se mantiene el
tema negro (ADR 0002), el contraste AA y `prefers-reduced-motion`.

## Goals / Non-Goals

**Goals:** consumir ese contrato con estados de carga/error/vacío; las cuatro mejoras de uso
diario con lógica pura testeable en `lib/`.

**Non-Goals:** estadísticas reales (la API no tiene versión de prompt ni «% útiles»; la página
sigue con datos de ejemplo), autenticación, caché entre páginas, búsqueda en servidor (`q`),
estado agregado del change (`review_status`, otra ronda de backend).

## Decisions

- **Fuente de datos inyectable (`data/source.tsx`).** Una interfaz `DataSource` (`projects`,
  `changes`, `change`) se provee por contexto. Por defecto es HTTP si existe `VITE_API_URL` y los
  datos de ejemplo si no; los tests inyectan una fuente propia. Así las páginas no saben de dónde
  vienen los datos y no hace falta simular `fetch` en cada test de página.
- **`lib/api.ts` solo habla HTTP y mapea.** `createHttpSource(baseUrl, fetchImpl)` valida el
  estado HTTP (`ApiError` con `status`), y convierte los DTO al modelo de vista (`Change`,
  `Review`, `Finding`). Se prueba con un `fetch` simulado, incluido 404, 5xx y red caída. El
  cursor es opaco: se reenvía tal cual con `encodeURIComponent`.
- **Modelo de vista.** `Change` añade `ref` y `url`; `sha` pasa a ser el SHA completo y se muestra
  abreviado (`shortSha`). `Review` añade `id` (varias ejecuciones por agente, no se puede usar el
  agente como key) y `findings` pasa de `string[]` a objetos `{severity, file, line, message}`.
  `Change.reviews` es opcional: el listado de la API no las trae.
- **Hook `useAsync` con reintento.** Devuelve `loading | error | ready`; ignora respuestas de
  peticiones obsoletas (cambio de ruta mientras carga) con una bandera de cancelación.
- **Paginación en el hook `useChannel`.** El filtro por tipo viaja al servidor (reinicia la lista
  y el cursor); la búsqueda y el estado se aplican en cliente sobre lo cargado. `mergeUnique`
  (por `id`) evita duplicados si el servidor repite un elemento al solaparse páginas. Un fallo al
  cargar más no borra lo ya mostrado: se avisa y se puede reintentar.
- **Filtro por estado en `lib/changeFilters.ts`.** «En curso» = alguna review en curso; «Con
  fallos» = alguna fallida; «Completados» = tiene reviews y todas completadas. No son
  excluyentes (una review en curso y otra fallida cumplen las dos primeras). Un change sin
  información de reviews (listado de la API) solo aparece en «Todos»: no se inventa un estado.
- **Hallazgos en `lib/findings.ts`.** `groupFindings` agrupa por archivo y ordena por severidad
  (`critical > high > medium > low > info`, resto al final) y línea. La severidad es texto libre
  en el backend, así que las desconocidas se muestran tal cual.
- **URL externa segura.** `change.url` viene de la ingesta (no es de confianza): `safeHttpUrl`
  solo admite `http:`/`https:` (evita `javascript:`) y el enlace lleva `rel="noopener noreferrer"`.
- **Copiar con alternativa.** `lib/clipboard.ts` usa `navigator.clipboard` y, si no está
  disponible o falla, un `textarea` temporal con `execCommand("copy")`. El botón anuncia el
  resultado en un `<output>` (región viva), no solo con color.

## Risks / Trade-offs

- Con la API real las cards no muestran resumen de reviews y el filtro por estado solo deja
  «Todos» útil hasta que el backend exponga el estado agregado (ronda 2 de backend); se cubre con
  el comportamiento descrito arriba, sin inventar datos.
- `GET /changes/{id}` no comprueba el proyecto de la ruta: el detalle muestra el slug de la URL.
- Cursores solo válidos con el mismo `kind`: por eso cambiar el filtro reinicia la paginación.
