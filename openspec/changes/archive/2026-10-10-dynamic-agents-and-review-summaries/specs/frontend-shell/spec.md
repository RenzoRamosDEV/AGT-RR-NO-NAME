## ADDED Requirements

### Requirement: Respuestas del canal con la API real
El canal SHALL mostrar en «Ver respuestas» las reviews ligeras que trae el listado (agente, estado,
nota y duración) de inmediato, y SHALL pedir el detalle completo del change (`GET /changes/{id}`)
al abrir el hilo cuando alguna review sea ligera, para mostrar resumen, hallazgos y motivo del fallo.
Mientras carga SHALL indicarlo; si falla SHALL avisar sin perder las reviews ligeras y ofrecer
«Reintentar». Un change sin reviews SHALL conservar en su resumen el badge del estado agregado en
lugar de quedarse vacío, y su hilo SHALL decir que aún no hay respuestas.

#### Scenario: Se abre un hilo
- **WHEN** el usuario abre «Ver respuestas» de un change con reviews ligeras
- **THEN** ve al instante los agentes con su estado, y cuando llega el detalle ve sus resúmenes y
  hallazgos

#### Scenario: El detalle falla
- **WHEN** el detalle del change falla al abrir el hilo
- **THEN** las reviews ligeras siguen visibles, aparece un aviso y «Reintentar» vuelve a pedirlo

#### Scenario: Reviews ya completas
- **WHEN** las reviews del change ya traen su resumen (datos de ejemplo)
- **THEN** no se pide el detalle

### Requirement: Agentes configurados en la interfaz
La interfaz SHALL tomar los nombres de los agentes de `agent_names` del diagnóstico del servidor y
mostrarlos con su nombre real (Claude y Codex con su nombre propio, cualquier otro tal cual
capitalizado) en la cabecera del canal, en el estado vacío y en Ajustes. NUNCA SHALL suponer
«Claude y Codex» ni un número fijo de agentes: mientras los agentes se desconocen (carga o fallo del
diagnóstico) el texto SHALL decir «los agentes configurados», y Ajustes SHALL mostrar un guion si el
servidor no informa de ninguno. El estado agregado de los datos de ejemplo SHALL calcularse con el
número de agentes de su propio diagnóstico.

#### Scenario: Agentes distintos de Claude y Codex
- **WHEN** el servidor informa `agent_names` = `agent_1`, `agent_2` y `gemini`
- **THEN** el canal dice «revisados por Agent_1, Agent_2 y Gemini» y Ajustes lista esos tres, sin
  mencionar a Claude

#### Scenario: Agentes desconocidos
- **WHEN** el diagnóstico falla o aún no ha respondido
- **THEN** el canal dice «revisados por los agentes configurados» sin nombrar ninguno

### Requirement: Detalle del run actual
El detalle de un change SHALL mostrar en las cards principales y en el panel de hallazgos solo las
reviews de su `run` actual (una review sin `run` cuenta como run 1), igual que el backend para su
estado y su resumen de hallazgos. Las reviews de runs anteriores SHALL mostrarse en secciones
colapsadas (`<details>`), una por run, de la más reciente a la más antigua, con el número de run y
de reviews en el título. Sin runs anteriores no SHALL haber sección colapsada.

#### Scenario: Tras un reintento
- **WHEN** el detalle de un change en el run 2 incluye reviews del run 1 y del run 2
- **THEN** el panel de hallazgos y las cards principales solo muestran las del run 2, y las del run 1
  quedan colapsadas bajo «Run 1 (anterior)»

#### Scenario: Un solo run
- **WHEN** todas las reviews son del run actual
- **THEN** no aparece ninguna sección colapsada
