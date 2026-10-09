# service-health Specification

## Purpose
Permite a un operador o a infraestructura externa (orquestador, monitor, CI) comprobar si
el proceso de la API está vivo, antes de que existan dependencias reales que verificar.

## Requirements

### Requirement: Liveness del proceso de la API
El sistema SHALL exponer un endpoint HTTP `GET /health` que responda sin depender de
ningún servicio externo (Postgres, Temporal, agentes), e indique únicamente que el
proceso de la API está en ejecución y puede aceptar peticiones.

#### Scenario: El proceso está en ejecución
- **WHEN** un cliente hace `GET /health` mientras el proceso de la API está arriba
- **THEN** la API responde `200 OK` con un cuerpo que indica estado saludable

#### Scenario: Disponible sin dependencias externas
- **WHEN** Postgres y Temporal no están disponibles o no están configurados todavía
- **THEN** `GET /health` sigue respondiendo `200 OK`, porque no comprueba esas
  dependencias (esa responsabilidad es de un futuro `GET /ready`)

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
