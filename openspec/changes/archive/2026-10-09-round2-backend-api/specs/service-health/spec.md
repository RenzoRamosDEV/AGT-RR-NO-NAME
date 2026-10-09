# Spec Delta

## ADDED Requirements

### Requirement: Diagnóstico de dependencias con latencia
El sistema SHALL exponer `GET /health/dependencies`, que responde siempre 200 con el estado
global (`ok` si todas responden, `degraded` si alguna falla) y, por cada dependencia
(Postgres y Temporal), su `status`, la `latency_ms` medida y, si falla, un `reason` de
vocabulario cerrado (`timeout` o `error`). NO SHALL incluir el texto de las excepciones ni
datos de conexión. Cada comprobación SHALL tener el mismo límite de tiempo que `/ready` y las
comprobaciones SHALL ejecutarse en paralelo.

#### Scenario: Todo disponible
- **WHEN** Postgres y Temporal responden
- **THEN** la respuesta es 200, `status` es `ok` y cada dependencia indica `ok` con su latencia

#### Scenario: Una dependencia caída
- **WHEN** Temporal falla con un error que contiene credenciales
- **THEN** la respuesta es 200, el estado global es `degraded`, Temporal indica `reason: error`
  y el cuerpo no contiene ningún fragmento del error original

#### Scenario: Dependencia lenta
- **WHEN** una comprobación supera el límite de tiempo
- **THEN** esa dependencia indica `reason: timeout` y las demás no se retrasan
