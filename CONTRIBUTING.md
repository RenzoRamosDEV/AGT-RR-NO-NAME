# Contribuir (notas para mí mismo)

Proyecto personal; esta guía es para mantener la disciplina del repo
consistente entre sesiones, no para colaboradores externos.

## Tests

Solo se añaden tests que aportan valor; la estrategia, las capas y el mapa del checklist
(qué está cubierto, qué diferido y por qué) están en [`docs/testing.md`](docs/testing.md).
Receta rápida: `just test-unit` (segundos, sin Docker) mientras desarrollas y `just ci`
antes de cada push.

## Revisión de código

La revisión de commits es cosa del producto, no de un agente de Claude Code: los dos agentes
de Duelo (Claude Code y Codex) revisan cada commit con el **mismo prompt versionado**,
`prompts/review/v2.md` (criterio: errores reales > seguridad > regresiones > tests > mejoras;
evidencia antes de reportar; nota 0–3 / 4–6 / 7–10 según el estado del cambio; severidades
`bug`, `risk`, `improvement`, `nit`). Cambiar el criterio es crear `v{n+1}.md`, nunca editar
una versión ya usada en reviews guardadas (spec `review-criteria`).

En `.claude/` solo quedan las skills de OpenSpec. Antes de un push o de un PR, la verificación
es determinista: `just ci`.

## Antes de tocar código

1. Lee `docs/spec/duelo.md` (spec completo) y `openspec/specs/`
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
