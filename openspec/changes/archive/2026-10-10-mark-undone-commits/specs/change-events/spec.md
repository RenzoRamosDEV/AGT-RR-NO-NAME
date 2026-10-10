## ADDED Requirements

### Requirement: Eventos de commits deshechos y revertidos
`GET /changes/{id}/events` SHALL incluir los eventos `commit.discarded`, `commit.restored` y
`commit.reverted` del change, en orden cronológico y con el payload reducido que ya usa la lista
blanca (sin datos internos).

#### Scenario: Commit deshecho
- **WHEN** el barrido marca un commit como deshecho
- **THEN** su línea de tiempo incluye `commit.discarded`

#### Scenario: Commit revertido
- **WHEN** se ingiere el revert de un commit
- **THEN** la línea de tiempo del original incluye `commit.reverted`
