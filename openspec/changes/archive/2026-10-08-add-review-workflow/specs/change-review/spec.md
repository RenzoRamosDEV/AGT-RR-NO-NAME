# Spec Delta

## Purpose

Permite al sistema ejecutar una review de un `Change` ya persistido mediante un workflow
durable que corre agentes de revisión en paralelo, persistiendo un resultado por agente
de forma atómica e idempotente, y sin que el fallo de un agente bloquee ni descarte el
resultado del otro.

## ADDED Requirements

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
