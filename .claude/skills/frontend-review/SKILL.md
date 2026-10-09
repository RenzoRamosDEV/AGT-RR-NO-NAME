---
name: frontend-review
description: Revisa cambios del frontend (React 19, Vite, TypeScript, Biome, Vitest) - corrección de componentes y hooks, estados de carga y error, render seguro de contenido no confiable (Markdown de las reviews), accesibilidad, rendimiento de render, cliente de API generado y tests. Úsalo al tocar frontend/src, estilos o configuración de Vite/TS/Biome, o cuando pidan "revisa el frontend".
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(pnpm exec biome:*), Bash(pnpm test:*), Bash(pnpm build:*), Bash(pnpm outdated:*)
---

# Revisión del frontend

El frontend vive en `frontend/` (organizado por funcionalidad en `src/features/*`; piezas
comunes en `src/components/` y `src/lib/`). Los comandos se ejecutan **desde `frontend/`**.

## Comprobaciones deterministas

`cd frontend && pnpm exec biome check .`, `pnpm test` (Vitest + Testing Library) y
`pnpm build` (`tsc -b && vite build`: el chequeo de tipos estricto vive aquí). Un fallo de
cualquiera es `BLOQUEANTE` `CONFIRMADO` si lo introduce el cambio.

## Qué buscar

**Corrección en React**
- Hooks: reglas de hooks, dependencias de `useEffect` incompletas o sobrantes, efectos que
  deberían ser derivados o handlers, estado derivado duplicado, claves de lista inestables
  (`key={index}` en listas que cambian).
- Condiciones de carrera al pedir datos (respuesta vieja pisa a la nueva), limpieza de
  suscripciones/timers/listeners, actualizar estado tras desmontar.
- Estados completos: **carga, vacío, error y éxito** de cada vista que depende de datos;
  fallo de red con mensaje útil y forma de reintentar.
- Router: rutas nuevas con estado de "no encontrado", parámetros validados antes de usarse.

**Seguridad (contenido no confiable)**
- El texto de las reviews y los diffs vienen de agentes y de código arbitrario: nunca
  `dangerouslySetInnerHTML` con ese contenido; Markdown renderizado con una librería que
  sanee (sin HTML crudo) y enlaces con `rel="noopener noreferrer"`.
- Tokens o secretos en el bundle (`VITE_*` es público), en `localStorage` sin necesidad o en
  el código.

**Accesibilidad y UX**
- Elementos interactivos reales (`button`, `a`), nombre accesible, foco visible y orden de
  foco, contraste suficiente (hay utilidades y tests de contraste en `src/lib/` y
  `src/styles/`), `prefers-reduced-motion` respetado (`useReducedMotion`), etiquetas en
  formularios, no transmitir información solo con color.

**Rendimiento**
- Renders innecesarios en listas largas, cálculos pesados en el render sin memoización
  justificada (no pidas `useMemo` por defecto), imágenes sin dimensiones, dependencias
  nuevas voluminosas para algo pequeño (mira el efecto en `pnpm build`).

**Contrato con la API**
- Los tipos del backend son la fuente de verdad: el cliente se genera desde OpenAPI
  (`docs/openapi.json`; `just gen-client` es un marcador hasta la Fase 4). Tipos escritos a
  mano que duplican los de la API, o datos de `src/data/mock.ts` que sobreviven al cableado
  real, son hallazgos.
- Los códigos de estado documentados (401, 404, 422, 503) tienen manejo en la UI.

**TypeScript y estilo**
- `any`, `as` que silencia un error real, `@ts-ignore` sin motivo, `!` sobre valores que
  pueden ser `undefined`. Biome ya cubre formato y buena parte de las reglas: no lo repitas.

## Tests

Un componente con lógica (estado, condiciones, eventos) tiene test con Testing Library
centrado en lo que ve el usuario (roles y textos, no detalles de implementación); las
utilidades puras con test unitario. No pidas tests de snapshots por defecto.
