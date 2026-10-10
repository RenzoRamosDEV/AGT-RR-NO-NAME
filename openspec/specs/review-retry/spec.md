# review-retry Specification

## Purpose
TBD - created by archiving change round2-backend-api. Update Purpose after archive.

## Requirements

### Requirement: Reintento de la review de un change
El sistema SHALL exponer `POST /changes/{id}/retry`, que exige `X-Ingest-Token` y, cuando el
`review_status` del change es `failed` o `partial_failed`, arranca una nueva ejecución de
review con el `run` siguiente y responde 202 con el id del change y su `run` actualizado. En
cualquier otro estado (`pending`, `running`, `completed`) SHALL responder 409 sin arrancar
nada; con un id inexistente, 404; sin token válido, 401. Una review completada NO SHALL
relanzarse. Dos reintentos simultáneos del mismo change SHALL producir una sola ejecución y
avanzar `run` una sola vez. Si no se puede arrancar la ejecución, SHALL responder 503 y dejar
el `run` sin cambios para poder reintentar.

#### Scenario: Reintento de una review fallida
- **WHEN** un change con `run = 1` y `review_status = failed` recibe `POST /changes/{id}/retry`
- **THEN** la respuesta es 202, el change pasa a `run = 2` y se arranca una ejecución para el run 2

#### Scenario: Fallo parcial
- **WHEN** el `review_status` es `partial_failed`
- **THEN** el reintento se acepta con las mismas garantías

#### Scenario: Nada que reintentar
- **WHEN** el `review_status` es `pending`, `running` o `completed`
- **THEN** la respuesta es 409 y no se arranca ninguna ejecución

#### Scenario: Change inexistente o sin token
- **WHEN** el id no existe, o falta o es inválido el token
- **THEN** la respuesta es 404, o 401 sin ningún efecto

#### Scenario: Doble petición simultánea
- **WHEN** llegan dos reintentos a la vez para el mismo change fallido
- **THEN** solo hay una ejecución del run siguiente y `run` avanza una vez

#### Scenario: Temporal no disponible
- **WHEN** el orquestador no puede arrancar la ejecución
- **THEN** la respuesta es 503 y el `run` del change no cambia

#### Scenario: Los ids en vuelo no cambian
- **WHEN** se arranca la review de un change con `run = 1`
- **THEN** el workflow id sigue siendo `{kind}-{project_id}-{head_sha}`; para `run > 1` lleva
  el sufijo `-r{run}`

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
