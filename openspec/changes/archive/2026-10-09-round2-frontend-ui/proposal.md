# Proposal

## Why

Tras la ronda 1 la interfaz sigue leyendo solo datos de ejemplo, aunque el backend ya define una
API de lectura (`round1-backend-api`). Esta ronda 2 de mejoras (propuesta por Codex) prepara el
frontend para consumirla —con estados de carga, error y vacío— y añade lo que más se echa de
menos en el uso diario: cargar más changes, filtrar por estado de review, ver los hallazgos
agrupados y copiar o abrir el change original.

## What Changes

- **Cliente de la API con estados reales:** `lib/api.ts` habla con `GET /projects`,
  `GET /projects/{slug}/changes` y `GET /changes/{id}`. Las páginas muestran carga, error con
  «Reintentar» y vacío. Sin `VITE_API_URL` se usan los datos de ejemplo, así que `pnpm dev` y los
  tests no necesitan backend.
- **«Cargar más» en el canal:** usa `next_cursor`, conserva filtros y búsqueda y no duplica
  changes.
- **Filtro por estado de review:** Todos / En curso / Con fallos / Completados.
- **Panel de hallazgos:** el detalle agrupa los findings por archivo, con severidad y agente.
- **Acciones del change:** abrir `url` en una pestaña nueva y copiar SHA o rama, con alternativa
  si no hay Clipboard API.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: añade estados de carga/error/vacío, paginación del canal, filtro por estado,
  panel de hallazgos y acciones del change.

## Impact

- `frontend/src`: `lib/api.ts`, `data/source.tsx` (fuente de datos inyectable), `data/mock.ts`,
  `features/**`, `layout/Shell.tsx`, `App.tsx`, `components/ReviewCard.tsx`, nuevos helpers en
  `lib/` y estilos en `index.css`.
- Sin dependencias nuevas y sin cambios de backend: se codifica contra el contrato de
  `round1-backend-api` y se prueba con un `fetch` simulado.
