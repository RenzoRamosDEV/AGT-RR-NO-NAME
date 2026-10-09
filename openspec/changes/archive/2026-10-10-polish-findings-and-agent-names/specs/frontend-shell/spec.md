## ADDED Requirements

### Requirement: Hallazgos sin ubicación
El panel de hallazgos y las cards de review SHALL NOT mostrar un archivo vacío o `N/A` ni una
línea no positiva. Los hallazgos sin archivo SHALL agruparse bajo «Sin archivo», siempre al final,
y conservar el orden por severidad.

#### Scenario: Hallazgo sin archivo ni línea
- **WHEN** una review trae un hallazgo con archivo `N/A` y línea `0`
- **THEN** el panel lo muestra bajo «Sin archivo» sin `N/A` ni `L0`

#### Scenario: Grupo sin archivo al final
- **WHEN** hay hallazgos con archivo y otros sin él
- **THEN** el grupo «Sin archivo» aparece después de todos los grupos con archivo

#### Scenario: Card con hallazgo sin ubicación
- **WHEN** una card de review lista un hallazgo sin archivo ni línea
- **THEN** muestra el mensaje sin la ubicación

### Requirement: Nombre de agente fiel
La interfaz SHALL mostrar el nombre real del agente de cada review. Solo `claude` y `codex`
SHALL tener nombre propio («Claude», «Codex»); cualquier otro agente SHALL mostrarse con su
nombre y un avatar de iniciales neutro, y SHALL NOT atribuirse a Claude.

#### Scenario: Agente desconocido
- **WHEN** una review llega con el agente `agent_1`
- **THEN** la card muestra «Agent_1» y un avatar «A1», no «Claude»

#### Scenario: Agente conocido
- **WHEN** una review llega con el agente `codex`
- **THEN** la card muestra «Codex»
