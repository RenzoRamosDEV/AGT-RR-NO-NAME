## ADDED Requirements

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
