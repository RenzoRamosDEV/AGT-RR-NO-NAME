# commit-ingestion Specification

## Purpose
Permite que un hook o cliente local envíe un commit por HTTP y que el sistema lo persista
y dispare su review sin duplicar trabajo, rechazando las peticiones no autorizadas.

## Requirements

### Requirement: Ingesta autenticada por token
El sistema SHALL aceptar `POST /ingest/commit` solo con una cabecera `X-Ingest-Token`
válida; sin token o con uno incorrecto SHALL responder 401 sin persistir nada ni arrancar
ninguna review.

#### Scenario: Token ausente
- **WHEN** se envía un commit sin cabecera `X-Ingest-Token`
- **THEN** la respuesta es 401, no se crea ningún `Change` y no se arranca ninguna review

#### Scenario: Token incorrecto
- **WHEN** se envía un commit con un `X-Ingest-Token` que no coincide con el configurado
- **THEN** la respuesta es 401, no se crea ningún `Change` y no se arranca ninguna review

### Requirement: La ingesta persiste el change y dispara la review
Para un commit de un proyecto existente, el sistema SHALL persistir el `Change` y arrancar
su review, respondiendo 202 con el identificador del change.

#### Scenario: Commit válido de un proyecto existente
- **WHEN** se envía un commit válido con token válido para un proyecto existente
- **THEN** la respuesta es 202 con el id del `Change` persistido y se arranca una review
  para ese change, que acaba produciendo una `Review` por cada agente configurado

### Requirement: Reingesta idempotente
El sistema SHALL tratar (proyecto, sha del commit) como identidad: enviar dos veces el
mismo commit SHALL devolver el mismo identificador de change sin duplicar el `Change`, su
evento ni la review.

#### Scenario: Mismo commit enviado dos veces
- **WHEN** se envía dos veces el mismo commit del mismo proyecto
- **THEN** ambas respuestas llevan el mismo id de change, existe un solo `Change` con un
  solo evento `change.created` y solo hay una ejecución de review para ese commit

### Requirement: Proyecto desconocido
El sistema SHALL responder 404 si el proyecto indicado no existe, sin persistir nada.

#### Scenario: Proyecto inexistente
- **WHEN** se envía un commit con token válido para un proyecto que no existe
- **THEN** la respuesta es 404 y no se crea ningún `Change` ni se arranca ninguna review

### Requirement: Diff acotado
El sistema SHALL recortar el diff recibido al máximo configurado y marcar el change con
`diff_truncated`, en vez de rechazar el commit o guardar un diff sin límite.

#### Scenario: Diff por encima del máximo
- **WHEN** se envía un commit cuyo diff supera el máximo configurado
- **THEN** el `Change` se guarda con el diff recortado a ese máximo y `diff_truncated`
  verdadero
