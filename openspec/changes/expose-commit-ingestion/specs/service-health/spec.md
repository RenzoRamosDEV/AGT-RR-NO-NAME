# Spec Delta

## ADDED Requirements

### Requirement: Readiness con dependencias reales
El sistema SHALL exponer `GET /ready`, que responde 200 solo si Postgres y Temporal son
alcanzables, y 503 indicando cuál dependencia falla en caso contrario. `GET /health` SHALL
seguir siendo independiente de ambas.

#### Scenario: Ambas dependencias disponibles
- **WHEN** Postgres y Temporal responden
- **THEN** `GET /ready` responde 200

#### Scenario: Postgres no disponible
- **WHEN** Postgres no responde y Temporal sí
- **THEN** `GET /ready` responde 503 e indica que falla Postgres, mientras `GET /health`
  sigue respondiendo 200

#### Scenario: Temporal no disponible
- **WHEN** Temporal no responde y Postgres sí
- **THEN** `GET /ready` responde 503 e indica que falla Temporal
