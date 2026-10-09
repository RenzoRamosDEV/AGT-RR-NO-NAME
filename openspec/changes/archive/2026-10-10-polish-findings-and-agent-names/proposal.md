# Proposal

## Why

Con la API real se vieron dos fallos de presentación. Los hallazgos sin archivo ni línea (el
agente de desarrollo envía `file: "N/A"` y `line: 0`) se muestran como `N/A` y `L0`. Y los agentes
que no son Claude ni Codex (`agent_1`, `agent_2`) aparecían como «Claude» en las cards, porque el
cliente de la API convertía cualquier nombre desconocido en `claude`.

## What Changes

- Un hallazgo sin archivo (vacío o `N/A`) se agrupa bajo «Sin archivo», al final, y un hallazgo
  sin línea (no positiva) no muestra la línea, tanto en el panel como en las cards.
- El cliente de la API conserva el nombre real del agente; `agentLabel` solo da nombre propio a
  Claude y Codex, y los demás se muestran tal cual con un avatar de iniciales neutro.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: presentación de hallazgos sin ubicación y de agentes desconocidos.

## Impact

- `frontend/src`: `data/mock.ts` (`AgentName` pasa a `string`), `lib/api.ts`, `lib/findings.ts`,
  `features/review/FindingsPanel.tsx`, `components/ReviewCard.tsx`,
  `components/ui/AgentAvatar.tsx` y tests.
- Sin dependencias nuevas y sin cambios de backend.
