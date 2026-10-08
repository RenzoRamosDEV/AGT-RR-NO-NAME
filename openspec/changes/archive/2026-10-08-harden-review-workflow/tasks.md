# Tasks

## 1. Estados tipados en el dominio

- [x] 1.1 Añadir `ChangeStatus` (`PENDING`) en `domain/change.py` y `ReviewStatus`
      (`COMPLETED`, `FAILED`) en `domain/review.py` como `StrEnum`; usarlos en
      `Change.new`, `Review.succeeded` y `Review.failed`; verificar con los tests de
      dominio existentes más una aserción nueva que compare contra el enum
      (`uv run pytest backend/tests/domain -q`).
- [x] 1.2 Adaptar `SqlAlchemyChangeRepository`/`SqlAlchemyReviewRepository` para guardar
      `.value` y reconstruir el enum al leer; verificar con los tests de integración
      existentes de `tests/adapters/` (los valores almacenados no cambian, no hay
      migración).

## 2. Workflows con IDs y un solo argumento dataclass

- [x] 2.1 Reemplazar `ChangeDTO` y la activity `load_change` por carga interna:
      `RunReviewInput` pasa a ser `(change_id, agent_name, run)` y `run_review` carga el
      `Change` con `ChangeRepository.get`; un `Change` inexistente lanza
      `ApplicationError(non_retryable=True)`; verificar que el diff ya no aparece en
      ningún dataclass de `workflows/dto.py` (`grep -n diff` vacío).
- [x] 2.2 Añadir `ReviewChangeInput(change_id, agent_names, run)` y
      `ReviewCommitInput(change_id, agent_names, run)`; los workflows reciben ese único
      argumento y propagan `run` (se elimina el `run=1`); actualizar los tests de
      `tests/workflows/` y añadir uno que arranque con `run=2` y compruebe en BD que las
      reviews quedan con `run=2`.
- [x] 2.3 `run_review` lanza `ApplicationError(non_retryable=True)` si el agente no está
      en el registro; añadir un test que lo provoque y compruebe que falla sin crear
      ninguna `Review` y sin reintentos (un solo intento de la activity).

## 3. Limpieza

- [x] 3.1 Eliminar `session_scope` de `adapters/persistence/db.py`; verificar que no queda
      ninguna referencia (`grep -rn session_scope backend/` vacío) y que `uv run mypy`,
      `ruff` y `lint-imports` siguen limpios.
- [x] 3.2 Verificación final: `just ci` en verde (suite completa con testcontainers y
      Temporal time-skipping).

## Workflow follow-up

- Archivar con `openspec archive harden-review-workflow --yes` tras mergear (no hay specs
  que fundir: `skip_specs`).
