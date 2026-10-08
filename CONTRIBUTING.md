# Contribuir (notas para mí mismo)

Proyecto personal; esta guía es para mantener la disciplina del repo
consistente entre sesiones, no para colaboradores externos.

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
