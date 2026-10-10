## ADDED Requirements

### Requirement: Reintento de un change atascado por fallo de infraestructura
Un change cuyo agente agotó los reintentos por fallo de infraestructura SHALL quedar con una review
fallida para ese agente y, por tanto, en estado `failed` o `partial_failed`, de modo que
`POST /changes/{id}/retry` lo acepte (202) en lugar de responder 409.

#### Scenario: Reintentar tras un fallo de infraestructura
- **WHEN** un agente agotó sus intentos y el change quedó `partial_failed`
- **THEN** `POST /changes/{id}/retry` responde 202 y arranca el `run` siguiente

### Requirement: El reintento reinicia el reloj de stale
Al avanzar el `run`, el sistema SHALL guardar el instante del reintento como inicio del nuevo `run`.

#### Scenario: Reloj tras el reintento
- **WHEN** se reintenta un change
- **THEN** su inicio de `run` es el instante del reintento y la creación del change no cambia
