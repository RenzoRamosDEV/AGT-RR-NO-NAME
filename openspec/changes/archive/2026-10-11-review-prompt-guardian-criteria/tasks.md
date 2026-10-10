# Tasks

## 1. Prompt versionado

- [x] 1.1 Escribir `prompts/review/v2.md` con el criterio de `code-guardian` generalizado (prioridades, qué buscar por familia, evidencia, qué no reportar, rúbrica 0–3/4–6/7–10, severidades, formato JSON, bloque de datos no confiables con `{mark}`) y borrar `prompts/review/.gitkeep`. Verificación: el fichero existe, contiene «{mark}» en el bloque de seguridad y la rúbrica con los tres tramos.
- [x] 1.2 `review_payload.py`: `PROMPT_VERSION = "v2"`, `load_instructions()` (raíz del repo, cacheada, `FileNotFoundError` con la ruta) y `build_prompt(change, nonce=None, instructions=None)` que la usa; `_INSTRUCTIONS` desaparece. Tests unitarios: el prompt sale del fichero (inyectar otro texto lo cambia), sin fichero falla nombrando la ruta, tras construir no queda `{mark}`, y contiene la rúbrica y la regla de evidencia; los tests existentes de delimitación/nonce/recorte siguen en verde. Verificación: `uv run pytest tests/unit/adapters/test_review_payload.py --no-cov`.

## 2. Fuera del flujo de Claude Code

- [x] 2.1 Borrar `.claude/agents/code-guardian.md`, `.claude/skills/guardian`, `.claude/hooks/guardian-readonly.py`, las 14 skills de revisión (`diff-review`, `bug-detection`, `security-audit`, `finding-verification`, `review-report`, `test-coverage`, `architecture-review`, `change-hygiene`, `data-and-api-contracts`, `dependency-and-config-audit`, `frontend-review`, `performance-review`, `safe-refactoring`, `temporal-review`) y `backend/tests/unit/tooling/test_guardian_readonly_hook.py`; dejar `.claude/skills/openspec-*`. Verificación: `grep -rn guardian --exclude-dir=archive .claude backend CONTRIBUTING.md docs` sin resultados y `just test-unit` en verde.
- [x] 2.2 Actualizar `CONTRIBUTING.md` (la revisión del producto sigue `prompts/review/v2.md`; el desarrollador verifica con `just ci`), `docs/architecture.md` (sección `cli-review-agents`: prompt versionado v2 y su criterio), `docs/temporal-buenas-practicas.md` (sin la skill: el checklist vive en el prompt y en los ADR) y `docs/testing.md` (quitar el test del hook si está listado). Verificación: ninguna referencia a `code-guardian` ni a skills borradas fuera de `openspec/changes/archive`.

## 3. Cierre

- [x] 3.1 `just ci` en verde y una review real de prueba con el worker (`AGENT_NAMES=claude,codex`) sobre un commit de este repo para ver que los dos agentes devuelven JSON válido con el prompt v2 y notas coherentes con la rúbrica. Verificación: salida de `just ci` y las dos reviews en la UI o en la API.

## Workflow follow-up

- Archivar el change (`openspec archive`) y commit/PR cuando el usuario lo pida.
