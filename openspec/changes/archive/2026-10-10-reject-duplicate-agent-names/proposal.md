# Proposal

## Why

La revisión de Codex de la PR de reutilización encontró que `AGENT_NAMES=agent_1,agent_1` (o
`claude,Claude`) se acepta. `reviews_to_reuse` convierte la lista en un `set`, así que una sola review
satisface «todos los agentes»: la PR copia 1 review y no arranca workflow, pero el resto del sistema
calcula el estado con `expected_agents = len(settings.agent_names)` = 2 y la PR queda `running` y,
con el tiempo, `stale`. Una lista con nombres repetidos es siempre un error de configuración.

## What Changes

- `Settings.agent_names` rechaza los nombres repetidos, sin distinguir mayúsculas, con un mensaje que
  nombra el duplicado; la API y el worker fallan al arrancar.
- `reviews_to_reuse` deja de compararse contra un `set`: con una lista de agentes con repetidos no
  reutiliza nada (defensa en profundidad si la lista llegara sin validar).
- Se documenta que el índice parcial de la migración `g7d5e9b3c126` se crea sin `CONCURRENTLY`: en una
  base grande conviene crearlo a mano con `CREATE INDEX CONCURRENTLY`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `cli-review-agents`: `AGENT_NAMES` no admite nombres repetidos.
- `review-reuse`: una lista de agentes con repetidos nunca reutiliza reviews.

## Impact

- `backend/src/duelo/config.py`, `backend/src/duelo/domain/review_reuse.py` y sus tests.
- `design.md` de `reuse-commit-reviews-for-prs` y README (nota sobre el índice).
