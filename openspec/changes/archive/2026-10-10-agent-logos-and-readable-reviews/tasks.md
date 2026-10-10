# Tasks

## 1. Logos y avatar

- [x] 1.1 Logos a `src/assets/agents/` (160×160) y `AgentAvatar` con tamaños 16/20/28/36, `decorative`, imagen para `claude` y `codex` (sin distinguir mayúsculas) y fallback de iniciales; tests unitarios
- [x] 1.2 Avatar en hilo de reviews, checks del canal, «está revisando…», Ajustes y Estadísticas; verificar con tests de render

## 2. Mini-markdown seguro

- [x] 2.1 `lib/markdown.ts` con tests felices (párrafos, saltos, código, negrita, cursiva, listas, vallas, enlaces) y hostiles (HTML, `javascript:`, imágenes, vallas sin cerrar, anidación profunda, entrada enorme)
- [x] 2.2 `components/Markdown.tsx`; verificar con test de render que no se inyecta HTML ni se enlaza nada que no sea http(s)

## 3. Reviews y hallazgos legibles

- [x] 3.1 `lib/recommendation.ts` con tests; `FindingCard` (severidad con icono, chip de ubicación copiable, mensaje, recomendación)
- [x] 3.2 `Collapsible` con estado recordado entre refrescos y remontajes; tests
- [x] 3.3 `ReviewCard` con jerarquía (cabecera, Resumen, Hallazgos) y pills de datos; `FindingsPanel` con contadores y filtro por severidad; estados vacío y de fallo
- [x] 3.4 Estilos en ambos temas, contraste AA, reduced motion; verificación visual en oscuro, claro y móvil

## 4. Cierre

- [x] 4.1 `pnpm lint`, `tsc -b`, `pnpm build`, `pnpm test` en verde; docs (ADR y `docs/spec/duelo.md`)
