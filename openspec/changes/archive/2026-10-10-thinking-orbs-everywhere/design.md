# Design

## Inventario de cargas y acciones en curso

| Dónde | Hoy | Con el change | Estado del orbe |
|---|---|---|---|
| `AsyncBoundary` (proyectos de `/`, canal, detalle, estadísticas, proyectos de Ajustes) | texto | `Busy` | `searching` |
| Diagnóstico de Ajustes (al cargar y con «Actualizar») | texto | `Busy` | `connecting` |
| Barra lateral, proyectos | «Cargando…» | `Busy` | `searching` |
| Hilo del canal, «Cargando respuestas…» | texto | `Busy` | `searching` |
| «Cargar más» | texto en el botón | `Busy` en línea | `working` |
| «Reintentar review» | texto en el botón | `Busy` en línea | `solving` |
| Añadir proyecto, Quitar proyecto, Sincronizar PRs | texto en el botón | `Busy` en línea | `connecting` |
| Review `running` de los datos de ejemplo | `AgentThinking` | `AgentThinking` sobre `Busy` | `working` |
| Agente esperado sin review (canal y detalle) | no se veía | `PendingAgents` | `working` |
| Refresco silencioso por sondeo | «Actualizado hace N s» | sin cambios | sin orbe |

## Un solo componente

`Busy` recibe `activity` (`load`, `more`, `agent`, `retry`, `connect`) y una `label`. El mapa
`ACTIVITY_STATE` traduce la actividad al estado de la librería, de modo que los significados viven
en un único sitio. Dos formas: región `<output aria-live="polite">` (cargas de página) y `inline`
(`<span>`, dentro de botones y de listas). El orbe va en un hueco fijo de 20 × 20 px y es
decorativo (`aria-hidden`): el nombre accesible es la etiqueta visible, no un `aria-label`
duplicado sobre el canvas.

Bajo `prefers-reduced-motion` no se monta ningún canvas: queda un «…» estático junto a la etiqueta,
como ya hacía `AgentThinking`.

## Sin orbe en el sondeo

El sondeo refresca cada ~5 s sin estado de carga (los datos anteriores siguen visibles). Un orbe
cada 5 s sería ruido constante y haría parpadear una página que ya está estable, así que ese
refresco conserva solo el texto discreto de `UpdatedAgo`. Lo que sí cambia solo es un agente
pendiente que entrega su review: su orbe desaparece cuando llega.

## Agentes pendientes

Con la API real una review no terminada no existe como fila, así que «revisando» solo se puede
inferir: un change `pending` o `running` espera a cada agente de `agent_names` (diagnóstico) que no
tiene review del run actual. `pendingAgents(change, agentNames)` es una función pura que cuenta
solo el run actual (`splitRuns`) y cualquier review del agente, también una `running` de los datos de
ejemplo (que ya se dibuja con su propia tarjeta), para no duplicar el orbe. Si los agentes aún no
se conocen (`null`: cargando o servidor que no los informa) y el change espera reviews, se muestra un
único orbe «Esperando a los agentes…» en lugar de inventar nombres. El mock expone
`[claude, codex]`.

## Riesgos

- Los canvas son costosos si se multiplican: en un canal con muchos changes en curso hay un orbe por
  agente pendiente. Es el tamaño de 20 px de la librería, y solo los changes `pending`/`running`
  los llevan; los terminados no.
- jsdom no implementa el contexto 2D del canvas: `test/setup.ts` ya lo sustituye por `null` y la
  librería lo tolera.
