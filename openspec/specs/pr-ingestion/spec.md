# pr-ingestion Specification

## Purpose
TBD - created by archiving change round1-backend-api. Update Purpose after archive.

## Requirements

### Requirement: Ingesta autenticada de PRs
El sistema SHALL aceptar `POST /ingest/pr` solo con una cabecera `X-Ingest-Token` válida;
sin token o con uno incorrecto SHALL responder 401 sin persistir nada ni arrancar ninguna
review.

#### Scenario: Token ausente
- **WHEN** se envía un PR sin cabecera `X-Ingest-Token`
- **THEN** la respuesta es 401, no se crea ningún `Change` y no se arranca ninguna review

### Requirement: La ingesta de un PR persiste el change y dispara la review
Para un PR de un proyecto existente, el sistema SHALL persistir un `Change` de tipo `pr` y
arrancar su review, respondiendo 202 con el identificador del change. Las reglas de proyecto
desconocido (404), entrada inválida (422), diff acotado y fallo del orquestador (503) SHALL
ser las mismas que las de la ingesta de commits.

#### Scenario: PR válido de un proyecto existente
- **WHEN** se envía un PR válido con token válido para un proyecto existente
- **THEN** la respuesta es 202 con el id de un `Change` de tipo `pr` y se arranca una review
  para ese change

#### Scenario: Proyecto inexistente
- **WHEN** se envía un PR para un proyecto que no existe
- **THEN** la respuesta es 404 y no se crea ningún `Change` ni se arranca ninguna review

### Requirement: Reingesta idempotente de PRs
El sistema SHALL tratar (proyecto, tipo, sha de la cabeza del PR) como identidad: enviar dos
veces el mismo PR SHALL devolver el mismo change sin duplicar el `Change`, su evento ni la
review. Un PR y un commit del mismo proyecto con el mismo sha SHALL ser changes distintos,
cada uno con su propia review.

#### Scenario: Mismo PR enviado dos veces
- **WHEN** se envía dos veces el mismo PR (mismo proyecto y `head_sha`)
- **THEN** ambas respuestas llevan el mismo id y solo hay una ejecución de review

#### Scenario: PR y commit con el mismo sha
- **WHEN** se envían un commit y un PR del mismo proyecto con el mismo sha
- **THEN** se crean dos changes distintos y se arrancan dos reviews
