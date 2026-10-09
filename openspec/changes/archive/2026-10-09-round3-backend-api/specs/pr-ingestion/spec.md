# Spec Delta

## ADDED Requirements

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
