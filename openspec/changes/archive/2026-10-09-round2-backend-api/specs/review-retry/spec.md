# Spec Delta

## ADDED Requirements

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
