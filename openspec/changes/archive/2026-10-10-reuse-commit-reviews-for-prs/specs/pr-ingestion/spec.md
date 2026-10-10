## ADDED Requirements

### Requirement: La respuesta de una PR indica si reutilizó las reviews
`POST /ingest/pr` SHALL añadir a su respuesta `202` el campo booleano `reused`, verdadero cuando el
change de la PR se creó con las reviews copiadas de su commit idéntico (y, al reenviarla, mientras
siga siendo una PR reutilizada del run 1). El campo es aditivo: el resto de la respuesta y los códigos
de estado no cambian.

#### Scenario: PR con reviews reutilizadas
- **WHEN** llega una PR cuyo commit idéntico ya está revisado por todos los agentes
- **THEN** la respuesta es `202` con `created: true` y `reused: true`

#### Scenario: PR que se revisa con normalidad
- **WHEN** la PR no puede reutilizar reviews
- **THEN** la respuesta lleva `reused: false` y se arranca su workflow como siempre
