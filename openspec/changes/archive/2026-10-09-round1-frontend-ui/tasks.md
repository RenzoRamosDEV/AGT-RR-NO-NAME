# Tasks

## 1. Sidebar móvil colapsable

- [x] 1.1 Botón "Menú" con `aria-expanded`/`aria-controls`, cierre al navegar y con Escape, estilos móviles; verificar con test de comportamiento

## 2. Buscador del canal

- [x] 2.1 `lib/search.ts` (título, autor, SHA) con tests unitarios, campo de búsqueda combinado con el filtro y estados vacíos; verificar con test de integración

## 3. Resumen por change

- [x] 3.1 `lib/reviewSummary.ts` con tests unitarios (conteo y plural) y badges en la card; verificar con test de render

## 4. Diff legible

- [x] 4.1 `lib/diff.ts` (`parseDiff`) con tests unitarios (rangos `@@`, numeración, cabecera simple), vista numerada y aviso de truncado (`Change.truncated`); verificar con test de render

## 5. Estadísticas visuales

- [x] 5.1 `lib/meter.ts` con tests unitarios (límites: máximo 0, sobrepasar 100) y barras decorativas en la tabla; verificar que los valores siguen en texto

## 6. Cierre

- [x] 6.1 `pnpm lint`, `pnpm build` y `pnpm test` en verde
