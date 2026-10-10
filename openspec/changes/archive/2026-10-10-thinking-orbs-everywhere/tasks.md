# Tasks

## 1. Componente

- [x] 1.1 `components/Busy.tsx` con el mapa actividad → estado, forma región y en línea, orbe decorativo de 20 px en un hueco fijo y alternativa «…» sin canvas bajo movimiento reducido; `AgentThinking` pasa a usarlo; verificar con tests de unidad (etiqueta, `role`, estado por actividad, reduced-motion sin canvas)

## 2. Cargas

- [x] 2.1 `AsyncBoundary` con `activity` (por defecto `load`), usado por `/`, canal, detalle, estadísticas, proyectos de Ajustes y el diagnóstico (`connect`); verificar con tests de integración de cada carga
- [x] 2.2 Barra lateral y «Cargando respuestas…» del canal con `Busy`; verificar con test de render

## 3. Acciones

- [x] 3.1 «Cargar más» (`more`), «Reintentar review» (`retry`), «Añadir», «Quitar proyecto» y «Sincronizar PRs» (`connect`) con orbe en línea y botón deshabilitado; verificar con tests de integración de cada acción

## 4. Agentes pendientes

- [x] 4.1 `lib/pending.ts` (`pendingAgents`) con tests de unidad: sin reviews, parcial, completo, run anterior, agentes desconocidos, estados terminados
- [x] 4.2 `PendingAgents` en las tarjetas del canal y en el detalle, con `agent_names` del diagnóstico y el mock `[claude, codex]`; verificar con tests de integración con `agent_1`, `agent_2` y review parcial

## 5. Cierre

- [x] 5.1 Capturas con Chrome headless contra la API real y revisión visual (orbes alineados, sin saltos de layout)
- [x] 5.2 `pnpm lint`, `tsc -b`, `pnpm build` y `pnpm test` en verde
