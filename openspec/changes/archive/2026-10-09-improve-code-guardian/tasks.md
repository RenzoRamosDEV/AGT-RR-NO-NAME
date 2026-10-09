# Tasks

## 1. Control de solo lectura

- [x] 1.1 Crear `.claude/hooks/guardian-readonly.py` con su batería de tests en
      `backend/tests/unit/tooling/` (comandos que deben bloquearse y comandos legítimos que
      deben pasar); verificar con `uv run pytest tests/unit/tooling --no-cov -q`.
- [x] 1.2 Actualizar el frontmatter y el flujo del agente (hook, `disallowedTools`, `skills`,
      política reformulada, sin worktrees, comando de `lint-imports` sin ambigüedad) y
      `background: false` en `guardian`; verificar que el frontmatter parsea.

## 2. Skills

- [x] 2.1 Matriz de comprobaciones en `diff-review` y reglas de veredicto en `review-report`
      (obligatoria / recomendada, "Lo que está bien" opcional); verificar coherencia entre
      ambas.
- [x] 2.2 Crear `temporal-review` y `frontend-review`, mover el contenido de Temporal de
      `bug-detection` y `performance-review`, y añadir las filas de triaje; verificar que los
      comandos y rutas citados existen en el repo.
- [x] 2.3 Ampliar `security-audit` (prompts y agentes) y `dependency-and-config-audit`
      (compatibilidad de runtime); recortar duplicados y mover las anécdotas a
      `change-hygiene/references/history.md`.

## 3. Verificación

- [x] 3.1 Prueba real con el agente registrado (`code-guardian` vía `Agent`) sobre un commit
      reciente: el informe respeta el formato, el hook no bloquea checks legítimos y
      `git status` queda idéntico.
- [x] 3.2 Actualizar `CONTRIBUTING.md`, `just ci` en verde, CI de GitHub en verde y archivar.
