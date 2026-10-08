# Proposal

## Por qué

Tras `add-review-workflow`, Codex (ronda 9) revisó el código real y señaló deuda técnica
que conviene pagar antes del siguiente change (`expose-commit-ingestion`), porque cada una
se encarece al añadir HTTP, reruns y diffs reales. Se verificó cada hallazgo contra el
código antes de aceptarlo (las 5 afirmaciones eran ciertas). Ninguna cambia el
comportamiento observable de la capacidad `change-review`, por eso este change no tiene
delta de specs (`skip_specs: true`).

## Qué cambia

- **El diff deja de viajar por el historial de Temporal.** Hoy `load_change` devuelve un
  `ChangeDTO` completo (con `diff`) que el workflow reenvía a cada `run_review`. Esto
  contradice la regla binding de `openspec/config.yaml` ("workflows y activities reciben
  IDs, no datos") y se encarece con diffs reales (límite de 2 MB por payload). `run_review`
  pasa a recibir solo `change_id`, `agent_name` y `run`, y carga el `Change` dentro de la
  activity. Se elimina la activity `load_change` y `ChangeDTO`.
- **Un solo argumento dataclass por workflow**, con `run` como campo explícito
  (`ReviewChangeInput`, `ReviewCommitInput`). Quita el `run=1` hardcodeado y permite
  añadir campos sin romper workflows en curso (buena práctica ya fijada en el spec).
- **Agente desconocido ya no provoca reintentos inútiles.** `self._agents[name]` lanzaba
  `KeyError` fuera del `try`: Temporal reintentaba 3 veces y no quedaba ninguna `Review`.
  Ahora es un `ApplicationError(non_retryable=True)`: error de configuración, no del agente.
- **`status` de `Change` y `Review` pasan a enums de dominio** (`ChangeStatus`,
  `ReviewStatus`) para evitar deriva entre dominio, BD y eventos antes de añadir API.
- **Se elimina `session_scope`** de `adapters/persistence/db.py`: nadie lo usa y su nombre
  sugiere una unidad de trabajo que en realidad no abre transacción ni hace commit.

Fuera de este change: cualquier endpoint HTTP, autenticación de ingesta, agentes reales
(siguiente slice, `expose-commit-ingestion`).

## Capacidades

### Nuevas capacidades

(ninguna)

### Capacidades modificadas

(ninguna - refactor interno sin cambio de comportamiento observable; ver `skip_specs`)

## Impacto

- `backend/src/review_arena/workflows/` (`dto.py`, `activities.py`, `review_change.py`,
  `review_commit.py`), `backend/src/review_arena/domain/` (`change.py`, `review.py`),
  `backend/src/review_arena/adapters/persistence/` (repositorios y `db.py`), y los tests
  de `backend/tests/` que los usan.
- Sin migración de datos: los valores almacenados de `status` no cambian
  (`"pending"`, `"completed"`, `"failed"`).
- Done-when: la suite completa sigue en verde, `run_review` ya no recibe ni transporta el
  diff, un agente desconocido falla sin reintentos, y `rerun` futuro puede pasar `run`
  sin tocar el workflow.
