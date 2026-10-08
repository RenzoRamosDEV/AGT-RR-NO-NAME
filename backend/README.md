# Review Arena - Backend

Monolito hexagonal en Python 3.12 (gestionado con `uv`): dominio y casos de uso puros,
adaptadores para Temporal/FastAPI/Postgres/GitHub/agentes, y tres entrypoints (API,
worker `platform`, worker `agents`). Ver `docs/architecture.md` y
`docs/spec/review-arena.md` en la raíz del repo para el diseño completo.

## Desarrollo local

```bash
uv sync                      # instala dependencias (incluye dev)
uv run pytest                # corre los tests
uv run lint-imports           # valida la regla de dependencias hexagonal
uv run ruff check .           # lint
uv run mypy .                 # tipos
```
