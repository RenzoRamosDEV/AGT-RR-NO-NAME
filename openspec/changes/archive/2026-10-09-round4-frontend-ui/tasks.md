# Tasks

## 1. Modelo y utilidades

- [x] 1.1 `data/mock.ts` (`reviewStatus`, `run`, metadatos de review, `agentStats`, `health`) y `lib/reviewStatus.ts` con tests (matriz de contadores), `lib/channelQuery.ts`, `lib/format.ts`, `lib/sanitize.ts`, `lib/ingestToken.ts` con tests unitarios; `sortRows` con nulos al final

## 2. Cliente y fuentes de datos

- [x] 2.1 `DataSource` + `createHttpSource` (`q`/`status`, `agentStats`, `health`, `retry`) con tests de `fetch` simulado (URL, cabecera de token, 202/401/404/409/503/red) y `createMockSource` coherente (filtros, estado agregado, reintento)

## 3. Estadísticas reales

- [x] 3.1 `StatsPage` con `agentStats()`, estados de carga/error/vacío, columnas nuevas, nulos «—», ordenación y barras; verificar con tests de integración

## 4. Filtros del canal en servidor

- [x] 4.1 `useChannel`/`ChannelPage` envían `q`/`kind`/`status`/`cursor`, retardo de búsqueda, reinicio de cursor al cambiar cualquier filtro, sin filtrado en cliente; eliminar `changeFilters.ts` y dejar `search.ts` solo para la fuente de ejemplo; verificar con tests (parámetros enviados, cursor reiniciado, sin mezclar respuestas)

## 5. Reintentar review

- [x] 5.1 Componente de reintento en el detalle (solo con fallo agregado, token en memoria, estados 202/401/404/409/503/red, un envío a la vez); verificar con tests de integración y que el token no llega a `localStorage`

## 6. Diagnóstico en Ajustes

- [x] 6.1 `SettingsPage` con proyectos y `health()`, latencia, degradación, motivos traducidos y «Actualizar»; verificar con tests (ok, degradado, error de una parte sin tapar la otra)

## 7. Metadatos de review

- [x] 7.1 `ReviewCard` con run, duración, nota y error sanitizado, insignia de estado agregado en la card del canal si no hay reviews; verificar con tests de render

## 8. Cierre

- [x] 8.1 `pnpm lint`, `tsc -b`, `pnpm build` y `pnpm test` en verde; `openspec validate round4-frontend-ui`
