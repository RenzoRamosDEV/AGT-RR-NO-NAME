# change-review Specification

## Purpose
Permite al sistema ejecutar una review de un `Change` ya persistido mediante un workflow
durable que corre agentes de revisión en paralelo, persistiendo un resultado por agente
de forma atómica e idempotente, y sin que el fallo de un agente bloquee ni descarte el
resultado del otro.

## Requirements

### Requirement: Dos reviews en paralelo por change
El sistema SHALL ejecutar, para un `Change` dado, dos agentes de revisión en paralelo y
persistir un resultado de `Review` por cada uno.

#### Scenario: Ejecución exitosa de ambos agentes
- **WHEN** se arranca una review para un `change_id` existente
- **THEN** quedan persistidas exactamente dos `Review`, una por cada agente configurado,
  cada una con su propio resultado

### Requirement: Fallo parcial no bloquea al otro agente
El sistema SHALL persistir el resultado del agente que tuvo éxito aunque el otro agente
falle durante la misma ejecución.

#### Scenario: Un agente falla, el otro no
- **WHEN** uno de los dos agentes lanza un error durante la review
- **THEN** la `Review` del agente que sí tuvo éxito queda persistida igualmente, y la del
  agente que falló queda registrada con estado de fallo en vez de perderse en silencio

### Requirement: Persistencia atómica e idempotente por agente
El sistema SHALL persistir cada `Review` junto con su evento (`review.completed` o
`review.failed`) en una única transacción, y SHALL tratar `(change_id, agent, run)` como
su identidad natural: reintentar la misma combinación SHALL ser idempotente.

#### Scenario: Reintento de la misma review no duplica
- **WHEN** se intenta persistir una `Review` para un `(change_id, agent, run)` que ya
  existe
- **THEN** no se crea una fila duplicada ni un segundo evento

### Requirement: Nombre de agente acotado
El sistema SHALL rechazar el registro de una `Review` cuyo nombre de agente esté vacío o
supere 50 caracteres, con un error de validación, antes de persistir nada.

#### Scenario: Nombre de agente en el límite
- **WHEN** se registra una review con un nombre de agente de exactamente 50 caracteres
- **THEN** la review se persiste

#### Scenario: Nombre de agente vacío o demasiado largo
- **WHEN** se registra una review con un nombre de agente vacío o de 51 caracteres
- **THEN** se rechaza con un error de validación y no se persiste nada

### Requirement: Contenido de review con carácter NUL
El sistema SHALL persistir una `Review` y su evento (`review.completed` o `review.failed`)
aunque su `summary`, `raw_output`, `error` o los textos de sus `findings` contengan el
carácter NUL, sustituyéndolo por U+FFFD, porque la base de datos no puede almacenarlo.

#### Scenario: Salida del agente con NUL
- **WHEN** un agente devuelve un resumen y un hallazgo cuyo texto contiene un NUL
- **THEN** la review se persiste y al leerla el texto contiene U+FFFD en lugar del NUL

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

### Requirement: Política de reintentos de las activities de review
Las activities de una review (`run_review` y su compensación) SHALL reintentarse como máximo 3
veces en total, con espera inicial de 1 s, backoff exponencial de coeficiente 2 y una espera máxima
entre intentos de 1 min. La política SHALL definirse en un único sitio compartido con los plazos,
de modo que el workflow y la configuración no diverjan.

#### Scenario: Fallo transitorio
- **WHEN** la activity falla dos veces por un error transitorio y la tercera tiene éxito
- **THEN** la review queda persistida una sola vez y no hay un cuarto intento

#### Scenario: Esperas acotadas
- **WHEN** se consulta la política con la que el workflow ejecuta `run_review`
- **THEN** sus valores son 3 intentos, 1 s inicial, coeficiente 2 y 1 min de espera máxima
