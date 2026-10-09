# Contribuir (notas para mí mismo)

Proyecto personal; esta guía es para mantener la disciplina del repo
consistente entre sesiones, no para colaboradores externos.

## Tests

Solo se añaden tests que aportan valor; la estrategia, las capas y el mapa del checklist
(qué está cubierto, qué diferido y por qué) están en [`docs/testing.md`](docs/testing.md).
Receta rápida: `just test-unit` (segundos, sin Docker) mientras desarrollas y `just ci`
antes de cada push.

## Revisión con Code Guardian

El agente `code-guardian` (`.claude/agents/`) revisa commits, ramas y PRs en solo lectura y
emite un veredicto (`APROBADO`, `APROBADO CON NOTAS`, `CAMBIOS REQUERIDOS`, `BLOQUEADO`).
Usa catorce skills (`.claude/skills/`): las de análisis (`bug-detection`, `security-audit`,
`architecture-review`, `test-coverage`, `performance-review`, `safe-refactoring`,
`dependency-and-config-audit`, `data-and-api-contracts`, `temporal-review`,
`frontend-review`) y las transversales (`diff-review`,
`change-hygiene`, `finding-verification`, `review-report`).

```text
/guardian                    # último commit de la rama
/guardian HEAD~3..HEAD       # un rango
/guardian 42                 # un Pull Request
/guardian backend/src/review_arena/application
```

Úsalo antes de cada push y de abrir un PR. Propone, no edita: no tiene `Edit`/`Write` y un
hook (`.claude/hooks/guardian-readonly.py`, con tests) bloquea los comandos `Bash` que
escriben. Los hooks de un agente de proyecto exigen aceptar la confianza del workspace.
Las correcciones las decides tú.
Los hallazgos llevan confianza (`CONFIRMADO`/`PROBABLE`/`HIPÓTESIS`); solo un `BLOQUEANTE`
confirmado bloquea.

## Antes de tocar código

1. Lee `docs/spec/review-arena.md` (spec completo) y `openspec/specs/`
   (comportamiento ya activo del sistema).
2. El trabajo se planifica con [OpenSpec](https://openspec.dev/): cada change
   vive en `openspec/changes/<nombre>/` con `proposal.md`, `design.md`,
   `specs/<capacidad>/spec.md` y `tasks.md`.
3. **No saltar de fase.** `openspec/config.yaml` fija el plan de 7 fases del
   spec; un change no debe implementar capacidades de una fase posterior
   solo porque "ya que estamos".

## Flujo de trabajo

```bash
pre-commit install   # una vez
just ci               # lint + test + validación de compose, antes de cada push
```

- Todo cambio (también mejoras, tests y tooling) va como change de OpenSpec, nunca como
  commit suelto.
- Conventional Commits (`feat:`, `fix:`, `chore:`, `ci:`, `docs:`...) -
  `commitlint` lo exige en CI.
- Cada ADR importante va en `docs/adr/NNNN-slug.md` y se enlaza desde
  `docs/architecture.md`.
- `just ci` reproduce localmente lo que corre en GitHub Actions (salvo
  `gitleaks`, `osv-scan`, `hadolint` y `commitlint`, que necesitan sus propios
  binarios/acciones y se validan mejor dejando que CI los corra).

## Al cerrar un change de OpenSpec

```bash
openspec archive <nombre-del-change>
```

Esto mueve el delta spec a `openspec/specs/` como spec activo y archiva el
change bajo `openspec/changes/archive/`.
