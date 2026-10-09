# rate-limiting Specification

## Purpose
Frenar el abuso de los endpoints de escritura sin afectar al uso normal.

## Requirements

### Requirement: Límite de peticiones en ingesta y reintento
Los endpoints `POST /ingest/commit`, `POST /ingest/pr` y `POST /changes/{id}/retry` SHALL limitar
el número de peticiones por IP de cliente en una ventana deslizante de `RATE_LIMIT_WINDOW_SECONDS`
(60 por defecto), con tope `RATE_LIMIT_REQUESTS` (300 por defecto); cada grupo (`ingest`, `retry`)
cuenta por separado. Superado el tope SHALL responder 429 con `Retry-After` (segundos enteros >= 1
hasta que se libere cupo) y sin ejecutar el caso de uso. El límite se aplica antes de validar el
token, así que las peticiones con token inválido también cuentan. Con `RATE_LIMIT_REQUESTS=0` el
límite SHALL estar desactivado. Las lecturas y `/health` NO SHALL limitarse.

#### Scenario: Se supera el tope
- **WHEN** una misma IP envía más peticiones que el tope dentro de la ventana
- **THEN** las sobrantes reciben 429 con `Retry-After` y no crean changes

#### Scenario: La ventana se desliza
- **WHEN** pasa la ventana desde las peticiones antiguas
- **THEN** la IP vuelve a poder enviar peticiones

#### Scenario: Grupos independientes
- **WHEN** una IP agota el cupo de ingesta
- **THEN** sigue pudiendo reintentar reviews mientras no agote el de `retry`

#### Scenario: Límite desactivado
- **WHEN** `RATE_LIMIT_REQUESTS=0`
- **THEN** ninguna petición recibe 429

#### Scenario: Token inválido también cuenta
- **WHEN** se envían peticiones con token inválido por encima del tope
- **THEN** las sobrantes reciben 429 en lugar de 401
