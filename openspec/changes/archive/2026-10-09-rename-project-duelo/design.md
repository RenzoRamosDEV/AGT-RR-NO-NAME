# Design

## Decisions

**Renombrado mecánico, verificado por la suite.** Sustitución de `review_arena` → `duelo`,
`review-arena` → `duelo` y `Review Arena` → `Duelo` sobre archivos versionados, excluyendo
`openspec/changes/archive/`, los lockfiles (se regeneran) y el worktree auxiliar. Un
`grep` posterior debe devolver cero coincidencias fuera de lo excluido, y `just ci` +
`just mutation` prueban que nada se rompió (los `source_paths` de `mutmut` y el contrato de
`import-linter` dependen del nombre del paquete).

**Se renombra también la base de datos de desarrollo.** Mantener `review_arena` como
usuario/BD dejaría el nombre antiguo en producto y credenciales. Coste: el volumen local no
se reutiliza (datos de prueba sin valor).

**El renombrado de la carpeta local es el último paso y manual.** La sesión de Claude Code
trabaja dentro de esa carpeta, y su memoria está indexada por ruta
(`~/.claude/projects/-var-home-renzo-Proyectos-new-project/`). Se copia a la clave nueva y se
indica reiniciar Claude Code desde `Duelo`. `git worktree repair` arregla el enlace del
worktree auxiliar.

**Remoto por SSH**, como indicó el usuario (la autenticación SSH ya funciona).

## Risks / Trade-offs

- [Riesgo] Una referencia al nombre antiguo que el `grep` no ve (por ejemplo, en un
  `uv.lock` o en variables de CI) → Mitigación: regenerar locks, correr CI y revisar la
  salida del `grep` final.
- [Riesgo] Entornos virtuales con el paquete instalado en modo editable bajo el nombre
  antiguo → Mitigación: `uv sync` tras el cambio.

## Open Questions

(ninguna)
