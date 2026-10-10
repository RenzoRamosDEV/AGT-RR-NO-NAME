# Proposal

## Why

La librería `thinking-orbs` ya está instalada, pero solo aparece en un sitio: el orbe de una review
«en curso» de los datos de ejemplo. Con la API real ese estado no existe (solo se guardan las
reviews terminadas), así que el orbe no se ve nunca, y el resto de cargas (listas, detalle,
estadísticas, diagnóstico, acciones de proyectos, reintento) se anuncian con texto plano. Queremos
que cualquier carga o acción en curso tenga el mismo indicador sobrio, y que el estado
«revisando» sea visible con la API real.

## What Changes

- Un único componente `Busy` envuelve `ThinkingOrb` (20 px, tema negro fijado) con una etiqueta
  visible, accesible (`<output>`) y con alternativa estática bajo `prefers-reduced-motion`. Un mapa
  semántico decide el estado del orbe: cargas → `searching`, «cargar más» y agentes revisando →
  `working`, reintento → `solving`, añadir/quitar proyecto, sincronizar PRs y diagnóstico →
  `connecting`.
- `AsyncBoundary`, la barra lateral, «Cargando respuestas…», «Cargar más» y los botones con envío en
  curso (reintentar, añadir, quitar, sincronizar) usan `Busy` sin cambiar la maquetación (el orbe
  reserva su hueco de 20 px).
- Nuevo `PendingAgents`: en las tarjetas del canal y en el detalle, un change `pending` o `running`
  muestra un orbe `working` por cada agente esperado (`agent_names` del diagnóstico) que aún no tiene
  review del run actual; desaparece cuando llega. El refresco silencioso por sondeo no lleva orbe.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: indicadores de carga y de acción en curso con `thinking-orbs`, y agentes
  pendientes visibles en el canal y el detalle.

## Impact

- `frontend/src`: nuevos `components/Busy.tsx`, `features/review/PendingAgents.tsx` y `lib/pending.ts`;
  cambios en `AgentThinking`, `AsyncBoundary`, `Shell`, `ChannelPage`, `ChangeDetailPage`,
  `SettingsPage`, `ProjectsSettings`, `AddProjectDialog`, `RetryReview`, estilos y tests.
- Sin dependencias nuevas (`thinking-orbs` ya estaba) y sin cambios de backend ni de contrato.
