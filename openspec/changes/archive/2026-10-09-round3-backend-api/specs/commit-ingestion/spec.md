# Spec Delta

## ADDED Requirements

### Requirement: La respuesta indica si el change se creó
La respuesta de `POST /ingest/commit` SHALL incluir `created`: `true` cuando la ingesta creó el
`Change` y `false` cuando ya existía (reingesta idempotente). El código de estado (202), el
identificador devuelto y los efectos de la reingesta SHALL ser los mismos en ambos casos.

#### Scenario: Primera ingesta
- **WHEN** se envía un commit que no existía
- **THEN** la respuesta es 202 con `created = true`

#### Scenario: Reingesta
- **WHEN** se envía de nuevo el mismo commit
- **THEN** la respuesta es 202 con el mismo `change_id` y `created = false`
