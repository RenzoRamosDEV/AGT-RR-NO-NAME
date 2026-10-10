## ADDED Requirements

### Requirement: Agentes configurados en el diagnóstico
`GET /health/dependencies` SHALL incluir `agent_names`: la lista de nombres de los agentes
configurados (`AGENT_NAMES`), en el orden configurado, para que un cliente no tenga que suponerlos.
SHALL contener solo esos nombres, nunca valores de configuración sensibles, y el campo SHALL ser
aditivo respecto al resto de la respuesta.

#### Scenario: Agentes por defecto
- **WHEN** un cliente hace `GET /health/dependencies` sin haber configurado `AGENT_NAMES`
- **THEN** `agent_names` es `["agent_1", "agent_2"]`

#### Scenario: Agentes configurados
- **WHEN** la API arranca con `AGENT_NAMES=agent_1,agent_2,gemini`
- **THEN** `agent_names` es `["agent_1", "agent_2", "gemini"]`
