# Tasks

## 1. Navegador de archivos del diff

- [x] 1.1 `lib/diff.ts`: reconocer `diff --git`/`---`/`+++`/`index` como metadatos, `file` por cabecera y `diffFiles` (recuentos); tests unitarios (formato ejemplo, git, sin cabecera) y lista con anclas en el detalle; verificar con test de render

## 2. Ordenación de estadísticas

- [x] 2.1 `lib/sort.ts` (`sortRows`, estable, sin mutar) con tests y cabeceras con botón y `aria-sort` en la tabla; verificar con test de integración (asc, desc, columna nueva)

## 3. Antigüedad del change

- [x] 3.1 `lib/relativeTime.ts` con tests (escalas, límites, futuro, fecha inválida), `createdAt` en el modelo y en `api.ts`, `NowProvider` y `<time>` en el canal; verificar con test de render con reloj fijo

## 4. Vista compacta del canal

- [x] 4.1 Interruptor Tarjetas/Compacta con `aria-pressed`, fila compacta y estilos responsive; verificar con test de integración (filtros se mantienen, hilo disponible)

## 5. Estado vacío accionable

- [x] 5.1 `lib/ingestHint.ts` (comando con slug y placeholder, URL base) con tests y estado vacío con botón de copiar; verificar que no hay token real y que con filtros activos no aparece

## 6. Cierre

- [x] 6.1 `pnpm lint`, `tsc -b`, `pnpm build` y `pnpm test` en verde; `openspec validate round3-frontend-ui`
