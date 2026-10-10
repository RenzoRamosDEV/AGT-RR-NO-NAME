## ADDED Requirements

### Requirement: El evento review.reused se expone en la línea de tiempo
`GET /changes/{id}/events` SHALL incluir los eventos `review.reused` de las reviews copiadas, con la
misma forma reducida que el resto (`id`, `type`, `created_at`, `agent`, `review_id`) y sin exponer el
resto del payload.

#### Scenario: PR con reviews reutilizadas
- **WHEN** se consulta la línea de tiempo de una PR cuyas reviews se copiaron
- **THEN** aparecen `change.created` y un `review.reused` por agente, por orden cronológico
