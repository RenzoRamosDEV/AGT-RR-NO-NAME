## ADDED Requirements

### Requirement: AGENT_NAMES no admite nombres repetidos
`AGENT_NAMES` SHALL rechazarse al arrancar la API o el worker si contiene el mismo nombre más de una
vez, sin distinguir mayúsculas. El error SHALL nombrar el duplicado. Una lista válida conserva el
orden y la escritura original de sus nombres.

#### Scenario: Nombre repetido
- **WHEN** `AGENT_NAMES=agent_1,agent_1`
- **THEN** la configuración falla y el mensaje nombra `agent_1`

#### Scenario: Repetido que solo difiere en mayúsculas
- **WHEN** `AGENT_NAMES=claude,Claude`
- **THEN** la configuración falla y el mensaje nombra el duplicado

#### Scenario: Lista válida
- **WHEN** `AGENT_NAMES=claude,codex`
- **THEN** la configuración la acepta tal cual
