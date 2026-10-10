## ADDED Requirements

### Requirement: Una lista de agentes con repetidos no reutiliza
Si la lista de agentes esperados contiene algún nombre repetido, el sistema SHALL NOT reutilizar
reviews: una review no puede satisfacer dos veces al mismo agente y el estado de la PR se calcula
contra la longitud de la lista. La configuración ya rechaza estas listas; esta regla evita que una
lista sin validar deje una PR en `running` sin workflow.

#### Scenario: Lista con un nombre repetido y una sola review
- **WHEN** los agentes esperados son `agent_1, agent_1` y el commit tiene una review de `agent_1`
- **THEN** no se reutiliza nada y la PR se revisa con normalidad
