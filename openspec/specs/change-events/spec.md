# change-events Specification

## Purpose
Línea de tiempo auditable de un change, con un payload reducido y estable.

## Requirements

### Requirement: Eventos de un change
El sistema SHALL exponer `GET /changes/{id}/events`, que devuelve los eventos del change en el
orden en que ocurrieron. Solo SHALL incluir los tipos `change.created`, `review.completed` y
`review.failed`, y de cada uno solo `id`, `type`, `created_at` y, cuando aplique, `agent` y
`review_id`. NO SHALL exponer la salida cruda de la review ni el texto del error de una review
fallida, ni ningún otro campo del payload. Un id inexistente SHALL responder 404.

#### Scenario: Historia completa
- **WHEN** un change fue creado y dos agentes terminaron, uno con éxito y otro con fallo
- **THEN** la respuesta es 200 con tres eventos en orden: `change.created`,
  `review.completed` y `review.failed`, cada review con su `agent` y `review_id`

#### Scenario: Payload redactado
- **WHEN** el evento `review.failed` tiene un `error` con el texto de una excepción
- **THEN** la respuesta no contiene ese texto ni el campo `error`

#### Scenario: Eventos de otros changes
- **WHEN** el proyecto tiene eventos de varios changes
- **THEN** solo se devuelven los del change pedido

#### Scenario: Tipos desconocidos
- **WHEN** el outbox contiene un evento de un tipo no incluido en la lista
- **THEN** no aparece en la respuesta

#### Scenario: Change inexistente
- **WHEN** el id no existe
- **THEN** la respuesta es 404

### Requirement: Orden cronológico estable
`GET /changes/{id}/events` SHALL devolver los eventos ordenados por `created_at` y, a igualdad de
instante, por `id`. El orden SHALL ser el cronológico aunque el `id` de un evento sea menor que el de
otro anterior en el tiempo.

#### Scenario: Eventos con id y fecha cruzados
- **WHEN** un evento con `id` menor tiene un `created_at` posterior al de otro con `id` mayor
- **THEN** la respuesta los lista por `created_at`, no por `id`

#### Scenario: Mismo instante
- **WHEN** dos eventos comparten `created_at`
- **THEN** salen ordenados por `id`

### Requirement: El evento review.reused se expone en la línea de tiempo
`GET /changes/{id}/events` SHALL incluir los eventos `review.reused` de las reviews copiadas, con la
misma forma reducida que el resto (`id`, `type`, `created_at`, `agent`, `review_id`) y sin exponer el
resto del payload.

#### Scenario: PR con reviews reutilizadas
- **WHEN** se consulta la línea de tiempo de una PR cuyas reviews se copiaron
- **THEN** aparecen `change.created` y un `review.reused` por agente, por orden cronológico

### Requirement: Eventos de commits deshechos y revertidos
`GET /changes/{id}/events` SHALL incluir los eventos `commit.discarded`, `commit.restored` y
`commit.reverted` del change, en orden cronológico y con el payload reducido que ya usa la lista
blanca (sin datos internos).

#### Scenario: Commit deshecho
- **WHEN** el barrido marca un commit como deshecho
- **THEN** su línea de tiempo incluye `commit.discarded`

#### Scenario: Commit revertido
- **WHEN** se ingiere el revert de un commit
- **THEN** la línea de tiempo del original incluye `commit.reverted`
