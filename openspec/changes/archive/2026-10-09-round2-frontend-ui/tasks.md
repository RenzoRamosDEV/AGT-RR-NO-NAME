# Tasks

## 1. Cliente de la API y estados de página

- [x] 1.1 `lib/api.ts` (`createHttpSource`, `ApiError`, mapeo DTO → modelo de vista) con tests de `fetch` simulado (éxito, cursor, 404, 5xx, red caída)
- [x] 1.2 `data/source.tsx` (contexto, fuente de ejemplo con paginación) y `lib/useAsync.ts` con reintento y descarte de respuestas obsoletas; páginas y `Shell` con carga/error/vacío

## 2. Cargar más

- [x] 2.1 `lib/pagination.ts` (`mergeUnique`) con tests y `useChannel` + botón «Cargar más»; test de integración con fuente de dos páginas, duplicado y fallo

## 3. Filtro por estado de review

- [x] 3.1 `lib/changeFilters.ts` con tests (combinaciones, sin reviews) y filtro en el canal

## 4. Panel de hallazgos

- [x] 4.1 `lib/findings.ts` (`groupFindings`) con tests (agrupar, orden, severidad desconocida) y panel en el detalle

## 5. Acciones del change

- [x] 5.1 `lib/clipboard.ts` y `lib/url.ts` (`safeHttpUrl`) con tests; botones «Abrir», «Copiar SHA» y «Copiar rama» con anuncio accesible

## 6. Cierre

- [x] 6.1 `pnpm lint`, `tsc -b`, `pnpm build` y `pnpm test` en verde; `openspec validate round2-frontend-ui`
