# Proposal

## Why

Con la ronda 2 la interfaz ya consume la API y permite filtrar y cargar más changes. Esta ronda 3
de mejoras (propuesta por Codex) pule la revisión del día a día: moverse por un diff grande,
ordenar las estadísticas, saber de cuándo es cada change, revisar muchos changes de un vistazo y
no quedarse en blanco ante un canal vacío.

## What Changes

- **Navegador de archivos del diff:** lista compacta de archivos tocados con sus líneas añadidas y
  borradas y enlaces que saltan a su sección del diff. El parser de diff reconoce también las
  cabeceras `diff --git`, `---`/`+++` e `index`.
- **Ordenación de estadísticas:** las cabeceras de la tabla son botones que ordenan por agente,
  prompt, % útiles, nota, duración o fallos, con `aria-sort`.
- **Antigüedad del change:** «hace 12 min» en el canal, con la fecha absoluta en un `<time>`.
- **Vista compacta del canal:** alterna entre tarjetas y filas densas.
- **Estado vacío accionable:** un proyecto sin changes muestra el comando mínimo para ingestar un
  commit con un token de ejemplo.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: añade navegador de archivos del diff, ordenación de estadísticas, antigüedad
  de los changes, vista compacta del canal y estado vacío accionable.

## Impact

- `frontend/src`: `lib/diff.ts`, `lib/sort.ts`, `lib/relativeTime.ts`, `lib/ingestHint.ts`
  (nuevos), `data/mock.ts` y `lib/api.ts` (`createdAt`), `features/**`, estilos en `index.css`.
- Sin dependencias nuevas y sin cambios de backend: `created_at` ya existe en el contrato de
  `round1-backend-api`.
