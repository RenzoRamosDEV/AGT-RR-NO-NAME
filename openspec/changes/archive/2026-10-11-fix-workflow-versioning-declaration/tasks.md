# Tasks

## 1. Corrección

- [x] 1.1 Quitar `versioning_behavior` (y el import de `VersioningBehavior`) de `review_change.py` y `review_commit.py`, dejando un comentario con el motivo. Verificación: `uv run ruff check`, `mypy` y `tests/integration/workflows` en verde, y el worker de desarrollo contra `just dev` completa una review (sin «deployment must be set» en el log).
- [x] 1.2 Corregir `docs/adr/0007` (decisión 1: la semántica no se declara al SDK; regla de validar contra el servidor real cualquier opción nueva), `docs/temporal-buenas-practicas.md` (WF-6 y VER-2) y `docs/testing.md` (comprobación manual contra el servidor real). Verificación: `grep -rn versioning_behavior backend/src docs` solo en el ADR y en los comentarios.

## Workflow follow-up

- Archivar el change y commit/PR junto con `review-prompt-guardian-criteria` cuando el usuario lo pida.
