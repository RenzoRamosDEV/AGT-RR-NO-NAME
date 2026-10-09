# Proposal

## Por qué

Las revisiones de este repo dependen hoy de que se pida a mano "revisa esto" y de la
disciplina de cada sesión: ya hemos visto fallos que un revisor sistemático habría parado
antes de llegar a `main` (un título de commit de 117 caracteres que rompió `commitlint`, un
secreto de ejemplo en el README que bloqueó `gitleaks`, un contenedor que arrancaba sin la
variable obligatoria y rompió el smoke test de CI, una sesión compartida entre repositorios
que solo el E2E destapó). Falta un criterio de revisión **explícito, reutilizable y
verificable**, con el mismo formato siempre, que sirva para commits, ramas y PRs.

## Qué cambia

- **Un agente, `code-guardian`** (`.claude/agents/code-guardian.md`): revisor de solo
  lectura que decide qué comprobar según el riesgo del diff, ejecuta las comprobaciones
  deterministas del repo y emite un veredicto (`APROBADO`, `APROBADO CON NOTAS`,
  `CAMBIOS REQUERIDOS` o `BLOQUEADO`). No modifica archivos y nunca presenta una hipótesis
  como un hecho.
- **Doce skills especializadas** en `.claude/skills/`, cada una responsable de una clase de
  problemas y con los criterios propios de este proyecto (hexagonal con `import-linter`,
  Temporal determinista, outbox, idempotencia, OpenSpec, umbrales de cobertura y mutación):
  `bug-detection`, `security-audit`, `architecture-review`, `test-coverage`,
  `performance-review`, `diff-review`, `safe-refactoring`, `dependency-and-config-audit`
  (las ocho de la propuesta original) más cuatro nuevas: `finding-verification` (protocolo
  anti-invención: nada se reporta sin evidencia), `review-report` (formato único, escala de
  severidad y confianza, puertas de veredicto), `change-hygiene` (Conventional Commits,
  trazabilidad con OpenSpec, atomicidad del commit) y `data-and-api-contracts` (migraciones,
  deriva modelo/esquema y compatibilidad del contrato OpenAPI).
- **Una skill de entrada, `guardian`** (`/guardian [commit|rango|PR|ruta]`), que lanza al
  agente en un contexto aislado sobre el objetivo indicado.
- Sección en `CONTRIBUTING.md` con cuándo y cómo usarlo.

Fuera de este change: ejecutar el agente automáticamente en CI o en un hook, publicar
comentarios en PRs, y aplicar correcciones (el agente propone, no edita).

## Capacidades

### Nuevas capacidades

Ninguna: es tooling de proceso sin comportamiento observable del producto
(`skip_specs: true`).

### Capacidades modificadas

Ninguna.

## Impacto

- Archivos nuevos en `.claude/agents/` y `.claude/skills/`; `CONTRIBUTING.md`.
- Sin cambios en `backend/`, `frontend/`, CI ni dependencias.
- Done-when: el agente y las skills tienen el formato oficial (frontmatter válido, nombres
  que coinciden con su carpeta, descripciones con disparadores), y una revisión real de un
  commit del repo produce un informe con el formato de `review-report`.
