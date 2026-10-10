## ADDED Requirements

### Requirement: Cuerpo del mensaje opcional en la ingesta
`POST /ingest/commit` y `POST /ingest/pr` SHALL aceptar un campo opcional `body` (cuerpo del mensaje
del commit, de hasta 20 000 caracteres) que sirve para detectar los commits de revert. Su ausencia
SHALL ser equivalente a una cadena vacía, de modo que los hooks ya instalados sigan funcionando. El
hook de git SHALL enviarlo acotado a 4 000 caracteres.

#### Scenario: Hook antiguo
- **WHEN** llega una petición sin `body`
- **THEN** se procesa igual que antes y no se detecta ningún revert

#### Scenario: Cuerpo demasiado largo
- **WHEN** `body` supera 20 000 caracteres
- **THEN** la API responde 422
