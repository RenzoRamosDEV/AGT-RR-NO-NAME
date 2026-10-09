# Proposal

## Por qué

Tras archivar `add-code-guardian`, se pidió a Codex una revisión crítica del agente y sus
skills (12 hallazgos, verificados uno a uno contra el repo y contra la documentación oficial
de Claude Code). Los que se sostienen son de dos tipos:

- **La garantía de solo lectura es de papel.** `Bash` sin restricciones puede escribir; las
  instrucciones se contradicen (permiten un `git worktree` o ejecutar `just mutation` y a la
  vez prohíben escribir); y `allowed-tools` en las skills solo concede permisos, no restringe
  (lo confirma la documentación). Hace falta un control ejecutable, no un párrafo.
- **Huecos y ambigüedades de revisión:** no hay ruta para el frontend (que ya existe con
  React 19, Vite, Vitest y Biome), ni cobertura específica de Temporal (replay determinista,
  versionado de workflows en vuelo, timeouts, compatibilidad de DTO), ni revisión de
  los propios prompts y agentes (superficie de inyección de prompts); "comprobación
  obligatoria" no está definida; el comando `cd backend && ... y uv run lint-imports` es
  ambiguo; la skill de entrada puede lanzarse en segundo plano (`background` es `true` por
  defecto con `context: fork`) aunque promete devolver el informe; y el agente no precarga
  las skills que usa siempre.

## Qué cambia

- **Control ejecutable de solo lectura:** un hook `PreToolUse` en el frontmatter del agente
  (`.claude/hooks/guardian-readonly.py`) bloquea comandos `Bash` que escriben, con tests; más
  `disallowedTools` para `Edit`, `Write` y `NotebookEdit`. Se reformula la política: el agente
  no modifica archivos versionados ni el árbol de trabajo; los artefactos que el repo ya
  ignora (`.coverage`, `mutants/`, `dist/`) se toleran. Se elimina el uso de worktrees.
- **Frontmatter oficial completo:** el agente precarga con `skills` las skills que usa
  siempre; la skill `guardian` fija `background: false`.
- **Matriz de comprobaciones por tipo de diff** (obligatorias / recomendadas) como única
  fuente en `diff-review`, y un veredicto coherente cuando falta una obligatoria.
- **Dos skills nuevas:** `frontend-review` y `temporal-review` (el contenido de Temporal que
  estaba repartido en `bug-detection` y `performance-review` pasa a la nueva).
- **Superficie de prompts y agentes** en `security-audit` (`.claude/**`, `prompts/review/**`,
  adaptadores de agentes) y **compatibilidad de runtime** en `dependency-and-config-audit`.
- **Recorte de contexto:** "Lo que está bien" pasa a opcional, las anécdotas de fallos pasados
  se mueven a una referencia no cargada por defecto, y se quitan duplicados entre el agente,
  `review-report` y `finding-verification`.

Descartado a propósito: la sección de observabilidad/evaluación (OpenTelemetry, Langfuse,
promptfoo) que propone Codex; todavía no existe en el código y el repo no diseña por
adelantado. Se añadirá cuando exista.

## Capacidades

Ninguna (tooling de proceso, `skip_specs: true`).

## Impacto

- `.claude/agents/code-guardian.md`, `.claude/hooks/guardian-readonly.py` (nuevo),
  `.claude/skills/*` (dos nuevas, varias editadas), `CONTRIBUTING.md`, tests del hook en
  `backend/tests/unit/tooling/`.
- Sin cambios en el código del producto ni en CI.
