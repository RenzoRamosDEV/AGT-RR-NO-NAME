## ADDED Requirements

### Requirement: Fallo de infraestructura registrado como review fallida
Cuando la ejecución de un agente agota sus reintentos por un fallo de infraestructura (la activity
falla en lugar de devolver un resultado), el sistema SHALL persistir una `Review` con estado `failed`
para ese `(change_id, agent, run)` y su evento `review.failed`, en vez de dejar el change sin
registro. El mensaje guardado SHALL ser genérico y NO SHALL incluir el texto de la excepción
original. Registrar el fallo SHALL ser idempotente (misma identidad natural, sin segunda fila ni
segundo evento) y NO SHALL cancelar ni descartar el resultado de los demás agentes. Un error de
configuración no reintentable (agente desconocido o change inexistente) NO SHALL registrar ninguna
review.

#### Scenario: Un agente falla por infraestructura y el otro completa
- **WHEN** la activity de un agente falla en todos sus intentos y la del otro termina bien
- **THEN** quedan dos reviews: `completed` la del agente sano y `failed` la del roto, con el change
  en `partial_failed`

#### Scenario: Compensación repetida
- **WHEN** se registra dos veces el fallo del mismo `(change_id, agent, run)`
- **THEN** hay una sola review y un solo evento `review.failed`

#### Scenario: Agente desconocido
- **WHEN** el workflow pide un agente que no está registrado
- **THEN** falla sin reintentos y no se persiste ninguna review

### Requirement: Latidos durante la review
Mientras un agente revisa, la activity SHALL emitir un latido a Temporal de inmediato y de forma
periódica (como máximo cada 10 segundos) hasta que el agente termine, para que una review lenta no
venza el `heartbeat_timeout`.

#### Scenario: Agente lento
- **WHEN** un agente tarda más de dos intervalos de latido en responder
- **THEN** la activity ha emitido al menos dos latidos antes de que termine
