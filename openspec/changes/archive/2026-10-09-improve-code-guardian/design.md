# Design

## Context

Ver `proposal.md`. Fuentes: revisión de Codex (`codex exec`, solo lectura) y verificación de
los campos de frontmatter contra la documentación oficial de Claude Code (skills y subagents).

## Decisions

**Una política, un control ejecutable.** "Solo lectura" significa: *no modifica archivos
versionados ni el árbol de trabajo*. Quedan permitidos los artefactos que `.gitignore` ya
excluye (`.coverage`, `mutants/`, `frontend/dist/`) porque son efecto inevitable de las
comprobaciones del repo. Se elimina `git worktree` (era la única escritura "permitida" y
contradecía la política). Para un commit que no es HEAD, el agente no ejecuta los checks
sobre ese árbol: lee el diff con `git show`, usa `gh run list --commit <sha>` como evidencia
de CI y declara en el informe que los checks locales corrieron sobre HEAD.

**Hook `PreToolUse` en el frontmatter del agente, no solo instrucciones.** La documentación
confirma que los subagentes admiten `hooks` y que `tools` no restringe `Bash` por patrón. El
hook (`guardian-readonly.py`, solo biblioteca estándar) recibe el comando por stdin y sale
con código 2 si detecta una escritura: redirecciones a archivo, `tee`, `sed -i`, borrados y
copias, subcomandos de `git` que cambian estado, instaladores, formateadores sin
`--check`/`--diff`, recetas `just` que escriben o levantan servicios, y `alembic
upgrade/downgrade`. Es una red de seguridad contra errores, no una defensa contra un
adversario (un script arbitrario puede escribir); por eso las instrucciones siguen diciendo lo
mismo y el informe verifica `git status`. Los hooks de un subagente de proyecto exigen que el
usuario acepte la confianza del workspace: se documenta.

**`disallowedTools: Edit, Write, NotebookEdit`** además de omitirlos de `tools`: explícito
y robusto si cambia la herencia de herramientas.

**`skills:` precarga lo que siempre se usa** (`diff-review`, `change-hygiene`,
`finding-verification`, `review-report`; ~300 líneas) y `Skill` queda en `tools` para cargar
bajo demanda las de análisis. No se precargan todas: gastaría contexto en cada revisión.

**`background: false` en `guardian`.** Con `context: fork` el valor por defecto es `true`
(requiere Claude Code ≥ 2.1.218); sin él la revisión se lanza en segundo plano y la skill
promete devolver el informe en el turno.

**Matriz de comprobaciones en `diff-review` (única fuente).** Por tipo de diff, qué es
*obligatorio* y qué *recomendado*. En `review-report`: una obligatoria que no se pudo ejecutar
limita el veredicto a `CAMBIOS REQUERIDOS` (el cambio no es verificable; no es `BLOQUEADO`
porque falta de evidencia no es un defecto confirmado); una recomendada no ejecutada limita
a `APROBADO CON NOTAS`.

**`temporal-review` y `frontend-review` como skills propias.** Temporal tiene reglas
específicas (replay, versionado con `workflow.patched`, timeouts y política de reintentos,
nombres de task queue, señales/queries, compatibilidad de DTO con campos por defecto) que
estaban diluidas en dos skills. El frontend existe y tiene sus propios comandos y riesgos
(render de Markdown no confiable de las reviews, estados de carga y error, accesibilidad,
cliente generado).

**Contexto: menos texto.** Las anécdotas de fallos del repo pasan a
`change-hygiene/references/history.md` (no se carga por defecto); "Lo que está bien" solo se
incluye si evita que alguien rompa algo; la regla "solo CONFIRMADO bloquea" vive únicamente
en `finding-verification` y las demás la referencian.

## Risks / Trade-offs

- [Riesgo] El hook bloquea una comprobación legítima → Mitigación: lista explícita y
  probada; un bloqueo devuelve un mensaje que el agente declara en "No verificado".
- [Riesgo] El hook da falsa sensación de seguridad → Mitigación: se documenta como red de
  seguridad; el cierre con `git status` se mantiene.
- [Riesgo] Más skills = más descripciones en contexto → Mitigación: descripciones concisas y
  triaje que solo carga las pertinentes.

## Open Questions

(ninguna)
