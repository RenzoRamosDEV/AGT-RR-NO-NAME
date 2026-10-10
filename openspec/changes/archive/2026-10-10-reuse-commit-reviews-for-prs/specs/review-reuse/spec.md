## ADDED Requirements

### Requirement: Una PR reutiliza las reviews de su commit idéntico
Al ingerir un change de tipo `pr`, el sistema SHALL buscar un change de tipo `commit` del mismo
proyecto con el mismo `head_sha` y el mismo diff (comparación exacta del diff almacenado y del indicador
`diff_truncated`). Si ese commit tiene una review `completed` de su `run` actual de **cada** agente
esperado (`AGENT_NAMES`, comparados por nombre exacto), el change de la PR SHALL crearse con una copia
de esas reviews (`agent`, `summary`, `score`, `findings`, `duration_ms`, estado `completed`, `run` 1) y
SHALL NOT arrancarse su workflow de Temporal. La copia SHALL NOT incluir `raw_output` ni `error`.

#### Scenario: Commit revisado y PR con el mismo SHA y diff
- **WHEN** un commit tiene reviews completadas de todos los agentes y llega una PR con su mismo SHA y
  diff
- **THEN** la PR nace con una review copiada por agente, su `review_status` es `completed` y no se
  arranca ningún workflow

#### Scenario: Diff distinto
- **WHEN** la PR tiene el mismo SHA pero un diff distinto (varios commits)
- **THEN** no se copia nada y la PR se revisa con normalidad

#### Scenario: SHA distinto o tipo distinto
- **WHEN** no existe un commit con el mismo SHA en el proyecto, o el change que llega es un commit
- **THEN** no se reutiliza nada

#### Scenario: Falta un agente o alguna review falló
- **WHEN** el commit solo tiene reviews de parte de los agentes esperados, o alguna está `failed`
- **THEN** no se reutiliza nada y la PR se revisa con normalidad

#### Scenario: El commit aún se está revisando
- **WHEN** llega la PR mientras el commit no tiene todas las reviews completadas
- **THEN** la PR se revisa con normalidad (límite conocido: no espera al commit)

### Requirement: La copia es atómica, idempotente y sin carreras
La copia de las reviews SHALL hacerse en la misma transacción que el alta del change y de su evento
`change.created`, y cada review copiada SHALL generar un evento `review.reused` con `agent`,
`review_id`, `change_id` y `reused_from_change_id`. Reenviar la PR SHALL NOT copiar reviews, crear
eventos ni arrancar un workflow; dos ingestas simultáneas de la misma PR SHALL dejar una sola review
por agente.

#### Scenario: Reingesta de una PR reutilizada
- **WHEN** se reenvía una PR cuyo change ya tiene reviews reutilizadas en su run 1
- **THEN** la respuesta indica `created: false`, no se duplica ninguna review ni evento y no se arranca
  ningún workflow

#### Scenario: Dos ingestas simultáneas
- **WHEN** dos peticiones idénticas de la misma PR se procesan a la vez
- **THEN** existe un único change con una review por agente y ningún workflow se arranca

#### Scenario: Una PR reintentada deja de estar reutilizada
- **WHEN** una PR con reviews reutilizadas se reintenta (`run` 2)
- **THEN** el reintento arranca los agentes con normalidad y las reviews del run 2 son propias

### Requirement: Marca de origen de la review reutilizada
Cada review copiada SHALL guardar el id del change del que procede en `reviews.reused_from_change_id`
(nullable, con clave foránea a `changes` y `ON DELETE SET NULL`). Las reviews propias SHALL tener ese
campo nulo.

#### Scenario: Se borra el commit de origen
- **WHEN** se elimina el change del que se copió una review
- **THEN** la review de la PR se conserva y su `reused_from_change_id` pasa a nulo
