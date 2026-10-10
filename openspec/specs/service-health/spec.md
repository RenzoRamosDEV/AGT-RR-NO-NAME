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

### Requirement: Agentes configurados en el diagnóstico
`GET /health/dependencies` SHALL incluir `agent_names`: la lista de nombres de los agentes
configurados (`AGENT_NAMES`), en el orden configurado, para que un cliente no tenga que suponerlos.
SHALL contener solo esos nombres, nunca valores de configuración sensibles, y el campo SHALL ser
aditivo respecto al resto de la respuesta.

#### Scenario: Agentes por defecto
- **WHEN** un cliente hace `GET /health/dependencies` sin haber configurado `AGENT_NAMES`
- **THEN** `agent_names` es `["agent_1", "agent_2"]`

#### Scenario: Agentes configurados
- **WHEN** la API arranca con `AGENT_NAMES=agent_1,agent_2,gemini`
- **THEN** `agent_names` es `["agent_1", "agent_2", "gemini"]`
