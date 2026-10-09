# 0002. Frontend con tema negro único

- Estado: Aceptada
- Fecha: 2026-10-09

## Contexto

El spec original (sección "Frontend") definía una estética tipo GitHub con tokens CSS, un
`--accent` elegible por el usuario y modo claro/oscuro según `prefers-color-scheme`. El
frontend seguía siendo un placeholder, así que no hay interfaz que migrar.

## Decisión

Un único tema negro (`color-scheme: dark` fijo, fondo `#000`) con acento monocromo. Se
mantienen los tokens CSS (`--bg`, `--surface`, `--border`, `--fg`, `--fg-muted`, `--accent`)
y la organización por funcionalidad. Los estados de carga de IA usan `border-beam` (borde
animado de la review en curso) y `thinking-orbs` (espera del agente), ambas de
libraries.dev (MIT), detrás de componentes propios y con fallback estático bajo
`prefers-reduced-motion`.

## Consecuencias

- Se descarta el modo claro y el color secundario configurable; si vuelven, se parte de los
  mismos tokens (Fase 4).
- Dos dependencias de terceros jóvenes en la UI; quedan aisladas en `AgentThinking` y
  `ReviewCard`, así que sustituirlas no toca el resto.
- El contraste AA de los tokens se comprueba en `frontend/src/styles/tokens.test.ts`.

Cambio de OpenSpec: `redesign-frontend-black`.
