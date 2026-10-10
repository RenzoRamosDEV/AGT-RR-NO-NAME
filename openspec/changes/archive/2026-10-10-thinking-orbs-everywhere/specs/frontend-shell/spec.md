## ADDED Requirements

### Requirement: Indicador de carga con orbes
Toda carga o acción en curso de la interfaz SHALL mostrar un orbe de `thinking-orbs` de 20 px, con
el tema negro fijado, junto a una etiqueta de texto visible, sin cambiar la maquetación (el orbe
reserva su hueco). El estado del orbe SHALL depender de la actividad: cargas de listas, páginas,
proyectos, detalle y estadísticas `searching`; «Cargar más» y agentes revisando `working`;
reintento de una review `solving`; añadir, quitar o sincronizar proyectos y el diagnóstico
`connecting`. El indicador SHALL ser accesible (región de estado anunciada con la etiqueta; el orbe
es decorativo) y, con `prefers-reduced-motion`, SHALL sustituir el orbe animado por un «…» estático
sin montar ningún canvas.

#### Scenario: Carga de una página
- **WHEN** el canal, el detalle, las estadísticas, los proyectos o el diagnóstico están cargando
- **THEN** se muestra su etiqueta («Cargando cambios…», «Comprobando dependencias…», etc.) con un
  orbe del estado que le corresponde

#### Scenario: Acción en curso en un botón
- **WHEN** el usuario envía «Reintentar review», «Añadir», «Quitar proyecto» o «Sincronizar PRs», o
  pulsa «Cargar más» y la petición está en curso
- **THEN** el botón queda deshabilitado y su texto lleva un orbe en línea del estado de esa acción

#### Scenario: Movimiento reducido
- **WHEN** el usuario prefiere movimiento reducido
- **THEN** ninguna carga monta un canvas animado y todas conservan su etiqueta de texto

#### Scenario: Sondeo silencioso
- **WHEN** una página se refresca sola por el sondeo
- **THEN** no aparece ningún orbe y los datos anteriores siguen visibles

### Requirement: Agentes pendientes de un change
Las tarjetas del canal y el detalle de un change con estado agregado `pending` o `running` SHALL
mostrar un orbe `working` con el nombre de cada agente esperado (`agent_names` del diagnóstico) que
aún no tiene review del run actual, y SHALL retirarlo cuando esa review llega. Un agente con review
de un run anterior SHALL seguir contando como pendiente en el run actual. Mientras los agentes
esperados no se conozcan, SHALL mostrarse un único orbe genérico en lugar de inventar nombres. Un
change `completed`, `failed` o `partial_failed` no SHALL mostrar agentes pendientes.

#### Scenario: Ninguna review todavía
- **WHEN** un change `pending` tiene agentes esperados `agent_1` y `agent_2` y ninguna review
- **THEN** se muestran dos orbes, «Agent_1 está revisando…» y «Agent_2 está revisando…»

#### Scenario: Review parcial
- **WHEN** `agent_1` ya entregó su review y `agent_2` no
- **THEN** solo queda el orbe de `agent_2`

#### Scenario: Todos entregaron
- **WHEN** el change pasa a `completed`
- **THEN** no queda ningún orbe de agente pendiente

#### Scenario: Reintento
- **WHEN** un change tiene reviews del run 1 y está `pending` en el run 2
- **THEN** ambos agentes figuran como pendientes del run 2

#### Scenario: Agentes desconocidos
- **WHEN** el diagnóstico aún no ha informado de los agentes y el change está `pending`
- **THEN** se muestra un único orbe «Esperando a los agentes…»
