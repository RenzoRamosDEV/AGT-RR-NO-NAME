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

### Requirement: La respuesta de un PR indica si el change se creó
La respuesta de `POST /ingest/pr` SHALL incluir `created`, con la misma semántica que en la
ingesta de commits: `true` si creó el change, `false` si ya existía un PR con el mismo proyecto
y `head_sha`.

#### Scenario: PR nuevo y repetido
- **WHEN** se envía dos veces el mismo PR
- **THEN** la primera respuesta lleva `created = true` y la segunda `created = false`, con el
  mismo `change_id`

#### Scenario: PR y commit con el mismo sha
- **WHEN** se envía un commit y después un PR del mismo proyecto con el mismo sha
- **THEN** ambas respuestas llevan `created = true`

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
