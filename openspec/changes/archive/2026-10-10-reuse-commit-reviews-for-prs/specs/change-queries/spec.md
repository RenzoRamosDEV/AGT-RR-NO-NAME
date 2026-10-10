## ADDED Requirements

### Requirement: Origen de una review reutilizada
Cada review del detalle (`GET /changes/{id}`) y cada review ligera del canal SHALL incluir el campo
`reused_from`: el id del change del que se copió, o `null` si la review es propia. El campo es
aditivo y no cambia ningún otro.

#### Scenario: Review copiada
- **WHEN** se consulta una PR cuyas reviews se reutilizaron
- **THEN** cada review lleva `reused_from` con el id del commit de origen

#### Scenario: Review propia
- **WHEN** se consulta un change revisado por sus agentes
- **THEN** `reused_from` es `null`
