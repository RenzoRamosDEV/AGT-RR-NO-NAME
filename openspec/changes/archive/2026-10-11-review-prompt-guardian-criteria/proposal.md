# Proposal

## Why

Los agentes que Duelo lanza sobre cada commit (Claude Code y Codex) reciben un prompt de un
párrafo: «busca bugs, seguridad, regresiones, tests; no inventes», con una nota 0–10 sin rúbrica.
Mientras tanto, el criterio de revisión bueno del proyecto — qué buscar, cómo verificar un
hallazgo antes de reportarlo, qué bloquea y cómo se puntúa — vive en el agente `code-guardian` y
sus skills de `.claude/`, que **solo usa el desarrollador en Claude Code**, nunca el producto, y
que además son específicas de este repo. El criterio debe estar en el producto, igual para los
dos agentes (el duelo tiene que ser justo), versionado como código, y desaparecer del flujo de
Claude Code, que no es su sitio.

## What Changes

- **Prompt de review v2, versionado en `prompts/review/v2.md`**, con el criterio de
  `code-guardian` generalizado a cualquier repositorio: prioridades (errores reales > seguridad >
  regresiones > tests > mejoras), qué buscar por familia (condiciones y límites, nulos, errores y
  recursos, estado y concurrencia, contratos; secretos, inyección, entrada, auth, fugas; lo
  eliminado en el diff, cambios de firma, coherencia con la intención), **protocolo de evidencia**
  (localizar, trazar, intentar refutar; solo hallazgos confirmados o probables, las hipótesis van
  al resumen como dudas), **rúbrica de nota** derivada del estado determinista (bloqueado 0–3,
  requiere cambios 4–6, aprobado 7–10) y mapeo de severidades (`bug`, `risk`, `improvement`,
  `nit`) con su definición. El prompt es el mismo para Claude y Codex; a quien tenga herramientas
  de lectura se le pide que verifique en el repo, y a quien no, que limite sus afirmaciones al
  diff.
- **El contrato JSON no cambia** (mismo esquema, mismas severidades): ni base de datos, ni API, ni
  frontend.
- **`code-guardian` sale de `.claude/`**: se eliminan el agente, el comando `/guardian`, el hook
  de solo lectura y las skills de revisión (`diff-review`, `bug-detection`, `security-audit`,
  `finding-verification`, `review-report`, `test-coverage`, `architecture-review`,
  `change-hygiene`, `data-and-api-contracts`, `dependency-and-config-audit`, `frontend-review`,
  `performance-review`, `safe-refactoring`, `temporal-review`) y su test del hook. Quedan las
  skills de OpenSpec. Las referencias en `CONTRIBUTING.md` y docs pasan a apuntar al prompt.
- Consecuencia asumida: el conocimiento específico de este repo que había en las skills («En
  este repo…») no cabe en un prompt genérico de producto y se pierde como guía de revisión;
  lo que era regla de arquitectura ya está en `openspec/config.yaml`, `docs/architecture.md` y
  los ADR.

## Capabilities

### New Capabilities
- `review-criteria`: el criterio con el que los agentes revisan un cambio: prioridades,
  evidencia exigida, rúbrica de la nota, severidades y versionado del prompt.

### Modified Capabilities

## Impact

- Código: `backend/src/duelo/adapters/agents/review_payload.py` (carga el prompt versionado;
  `_INSTRUCTIONS` deja de estar inline), `prompts/review/v2.md` (nuevo).
- Borrado: `.claude/agents/code-guardian.md`, `.claude/commands/*guardian*`,
  `.claude/hooks/guardian-readonly.py`, las 15 skills de revisión,
  `backend/tests/unit/tooling/test_guardian_readonly_hook.py`.
- Tests: unitarios del prompt (viene del fichero versionado, conserva las marcas y contiene
  la rúbrica y la regla de evidencia).
- Docs: `CONTRIBUTING.md`, `docs/architecture.md` (`cli-review-agents` → prompt v2),
  `docs/temporal-buenas-practicas.md` (ya no hay skill `temporal-review`), `docs/testing.md`.
- Sin cambios en API, base de datos ni frontend. Las reviews ya guardadas se hicieron con el
  prompt v1 (inline) y no se marcan: el campo `prompt_version` de la spec sigue pendiente.
