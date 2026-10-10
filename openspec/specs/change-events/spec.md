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
