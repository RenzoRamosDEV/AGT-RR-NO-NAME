# Tasks

## 1. Skills

- [x] 1.1 Crear las cuatro skills transversales (`finding-verification`, `review-report`,
      `diff-review`, `change-hygiene`); verificar que el frontmatter parsea y que `name`
      coincide con el directorio.
- [x] 1.2 Crear las ocho skills de análisis (`bug-detection`, `security-audit`,
      `architecture-review`, `test-coverage`, `performance-review`, `safe-refactoring`,
      `dependency-and-config-audit`, `data-and-api-contracts`); misma verificación.

## 2. Agente y entrada

- [x] 2.1 Crear `.claude/agents/code-guardian.md` (solo lectura, triaje por riesgo,
      veredicto) y la skill de entrada `guardian`; verificar frontmatter y que las skills que
      nombra existen.

## 3. Documentación y verificación

- [x] 3.1 Documentar el uso en `CONTRIBUTING.md`; verificar con `openspec validate
      add-code-guardian --strict`.
- [x] 3.2 Prueba real: lanzar el agente sobre un commit reciente del repo y comprobar que el
      informe respeta `review-report` y que no deja cambios en el árbol (`git status`).
      Hecho sobre `ef2ceec`: el informe destapó dos defectos reales (ver
      `fix-ingest-edge-cases`) y mejoras a las skills, ya aplicadas.
- [ ] 3.3 Verificación final: `just ci` en verde (los hooks de pre-commit pasan) y CI de
      GitHub en verde; archivar el change.
