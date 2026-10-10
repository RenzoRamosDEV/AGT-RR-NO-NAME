# Proposal

## Why

Con agentes reales (Claude Code y Codex) lo que devuelven las reviews se ve mal: el resumen es un
párrafo pegado, los backticks (`` `código` ``) salen literales, los hallazgos son citas oscuras con
texto largo y la ruta del archivo queda diminuta al final. Además cada agente se identifica con un
cuadrado de color con una inicial, cuando el usuario aporta los logos de Claude y de Codex para
usarlos como avatar.

## What Changes

- Los agentes `claude` y `codex` se muestran con su logo en todos los avatares (hilo de reviews,
  checks de las filas del canal, «está revisando…», Ajustes y Estadísticas); los demás siguen con
  iniciales de color. Un único `AgentAvatar` con tamaños 16, 20, 28 y 36, con alternativa de
  iniciales si la imagen no carga.
- El texto de las reviews (resumen y mensajes de hallazgos) se pinta con un mini-markdown propio y
  seguro: párrafos, saltos de línea, `código en línea`, negrita, cursiva, listas, bloques de código
  y enlaces http(s). Cualquier otra cosa se escapa como texto.
- Las reviews se presentan con jerarquía y ritmo de lectura: cabecera (agente, etiqueta APP,
  estado, datos en pills), bloque «Resumen» y «Hallazgos (N)».
- Cada hallazgo es una tarjeta con la severidad coloreada y con icono, la ubicación `archivo:línea`
  como chip copiable, el mensaje y la recomendación separada cuando el texto la trae.
- El panel de hallazgos del detalle cuenta por severidad y permite filtrar.
- Los textos largos se pliegan con «Ver más / Ver menos» y el estado se recuerda aunque la página
  se refresque sola.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: avatares de agente con logo y presentación legible de las reviews.

## Impact

- `frontend/src`: `components/ui/AgentAvatar.tsx`, `components/ReviewCard.tsx`, componentes nuevos
  (`Markdown`, `FindingCard`, `Collapsible`), `lib/markdown.ts`, `lib/recommendation.ts`,
  `features/review/FindingsPanel.tsx`, `features/review/PendingAgents.tsx`, canal, Ajustes,
  Estadísticas, estilos y tests.
- `frontend/src/assets/agents/`: los dos logos (160×160).
- Sin dependencias nuevas, sin cambios de backend ni de API.
