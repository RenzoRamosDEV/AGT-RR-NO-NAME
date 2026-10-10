## ADDED Requirements

### Requirement: Review reutilizada visible
La interfaz SHALL mostrar en una review con `reused_from` una pill discreta «Reutilizada del commit
<sha corto>» (con `title` y texto accesible) y SHALL NOT mostrar el indicador «está revisando…» de
los agentes en un change cuyas reviews se reutilizaron.

#### Scenario: PR con reviews reutilizadas
- **WHEN** se abre el detalle de una PR con reviews reutilizadas
- **THEN** cada review muestra la pill con el SHA corto y no hay orbe de agentes pendientes

#### Scenario: Review propia
- **WHEN** una review no trae `reused_from`
- **THEN** no se muestra la pill
