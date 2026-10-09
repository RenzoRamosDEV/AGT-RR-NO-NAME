# Proposal

## Why

El frontend es un placeholder de Fase 0 (`App.tsx` con un título). El spec de la Fase 4 describe un
front tipo Slack con estética de GitHub y tema claro/oscuro. Se redefine la dirección visual: un
único tema negro, sobrio y elegante, con estados de carga de IA cuidados, para que el portafolio
se vea profesional desde el primer momento y las fases siguientes construyan sobre un sistema de
diseño.

## What Changes

- Sistema de diseño negro (tokens CSS, tipografía, espaciado, superficies, bordes finos) que
  sustituye al `system-ui` claro/oscuro actual. **BREAKING** respecto a `docs/spec/review-arena.md`
  (tema "GitHub", `--accent` elegible, `prefers-color-scheme`): el tema es solo negro.
- Layout de aplicación: barra lateral con canales por proyecto + sección General, y rutas
  `/p/:slug`, `/p/:slug/changes/:id`, `/stats`, `/settings`.
- Pantallas maquetadas con datos de ejemplo locales (aún no existe API de lectura en el backend):
  canal con hilos desplegables, detalle de change con las dos reviews, estadísticas y ajustes.
- Estados de carga/"pensando" de la IA con librerías de libraries.dev: `border-beam` (borde
  animado en reviews en curso) y `thinking-orbs` (espera de un agente). Respetan
  `prefers-reduced-motion`.
- Accesibilidad: teclado completo, `aria-expanded` en hilos, contraste AA.

## Capabilities

### New Capabilities
- `frontend-shell`: apariencia (tema negro), navegación y representación de estados de review
  (en curso, completada, fallida) en la interfaz web.

### Modified Capabilities

(ninguna: no hay specs de frontend en `openspec/specs/`)

## Impact

- `frontend/`: nuevo `src/` por funcionalidad (`features/*`, `components/ui`, `styles`), `index.html`.
- Dependencias nuevas: `react-router`, `border-beam`, `thinking-orbs` (React 19 compatible).
- Fuera de alcance: API de lectura, SSE, TanStack Query, cliente generado, Monaco, voto ciego y
  color secundario configurable (siguen en Fase 4/6). Sugerido: ADR en `docs/adr/` por el cambio
  de dirección visual y actualizar la sección Frontend del spec.
