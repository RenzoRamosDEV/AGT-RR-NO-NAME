# Design

## Context

`frontend/` es un scaffold Vite + React 19 + TS strict con Biome. Sin router y sin estilos más
allá de `index.css`. El backend solo expone `/health` e ingesta; no hay API de lectura, así que
las pantallas usan datos de ejemplo tipados. Ver proposal.md (Why).

## Goals / Non-Goals

**Goals:** sistema de diseño negro reutilizable; estructura `features/*` del spec; estados de
carga de IA; accesibilidad base.

**Non-Goals:** datos reales, SSE, TanStack Query, Monaco, voto ciego, tema configurable.

## Decisions

- **Tokens CSS en `:root`** (`--bg`, `--surface`, `--border`, `--fg`, `--fg-muted`, `--accent`)
  con `color-scheme: dark` fijo. Alternativa: Tailwind; descartada para no sumar tooling y
  mantener los tokens del spec.
- **Acento monocromo** (blanco/plata), sin color elegible: el `--accent` configurable queda
  diferido a Fase 4.
- **`react-router`** para las 4 rutas del spec.
- **`border-beam`** envuelve la tarjeta de review en curso; **`thinking-orbs`** en la espera de
  un agente. Ambas MIT, React ≥18. Detrás de wrappers propios (`AgentThinking`, `ReviewCard`)
  para poder sustituirlas.
- **Datos de ejemplo** en `features/*/mock.ts` con tipos mínimos que luego dará el cliente
  generado.
- **Movimiento reducido**: un hook `useReducedMotion` decide entre animación y fallback estático.

## Risks / Trade-offs

- Desvío del spec (tema claro/oscuro estilo GitHub) → registrar ADR en `docs/adr/` y actualizar
  la sección Frontend.
- Librerías jóvenes con API desconocida hasta instalarlas → aisladas tras wrappers y cubiertas
  con build y tests de render.
- Los mocks pueden divergir del contrato real → tipos mínimos, sustituibles en Fase 4.
