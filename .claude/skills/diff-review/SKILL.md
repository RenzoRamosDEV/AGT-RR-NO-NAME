---
name: diff-review
description: Revisa el diff de un commit, rango, rama o Pull Request - clasifica el riesgo, identifica regresiones y decide qué otras skills de revisión hacen falta. Es el primer paso de toda revisión. Úsalo cuando pidan revisar un commit, un PR, "los últimos cambios" o "lo que acabo de hacer".
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(git log:*), Bash(git status:*), Bash(git blame:*), Bash(git merge-base:*), Bash(gh pr view:*), Bash(gh pr diff:*)
---

# Revisión del diff

Prioriza el código modificado y lo que depende de él. No audites el repositorio entero.

## 1. Delimita el objetivo

| Te piden | Comando |
| --- | --- |
| Un commit | `git show --stat <sha>` y `git show <sha>` |
| Un rango o rama | `git diff --stat <base>...HEAD` (base: `git merge-base origin/main HEAD`) |
| Cambios sin commitear | `git diff --stat` y `git diff --staged --stat` |
| Un PR | `gh pr view <n>` y `gh pr diff <n>` |
| Nada concreto | El último commit de la rama; dilo en el informe |

Lee el mensaje o la descripción: la **intención declarada** es el criterio contra el que se
juzga el cambio.

## 2. Triaje por riesgo (decide qué skills cargar)

| Si el diff toca... | Carga además |
| --- | --- |
| Lógica en `domain/` o `application/`, condiciones, bucles, parseo | `bug-detection` |
| Entradas externas, auth, SQL, secretos, serialización, HTTP; también `.claude/**`, `prompts/review/**` y adaptadores de agentes | `security-audit` |
| Imports entre paquetes, estructura nueva, puertos/adaptadores | `architecture-review` |
| Cualquier código de producción nuevo o cambiado | `test-coverage` |
| Una consulta o `await` dentro de un bucle nuevo, un `WHERE`/`ORDER BY` nuevo, o un campo nuevo en un DTO de workflow/activity (no basta con tocar `adapters/`) | `performance-review` |
| Código duplicado, funciones largas, renombrados | `safe-refactoring` |
| `pyproject.toml`, `uv.lock`, `package.json`, `Dockerfile`, `docker-compose.yml`, `.github/`, `justfile`, variables de entorno | `dependency-and-config-audit` |
| `alembic/`, `models.py`, routers, schemas, `docs/openapi.json` | `data-and-api-contracts` |
| `backend/src/duelo/workflows/`, `worker.py`, adaptadores de orquestación, DTOs de workflow | `temporal-review` |
| `frontend/`, `*.tsx`, estilos, config de Vite/TS/Biome | `frontend-review` |
| Siempre | `change-hygiene` (commit, OpenSpec) y `finding-verification` + `review-report` |

Un cambio solo de documentación o de tests no necesita las skills de seguridad ni de
rendimiento; dilo en el resumen en vez de forzarlas.

## 2b. Matriz de comprobaciones (única fuente)

*Obligatoria* = sin ella el cambio no es verificable; *recomendada* = aporta confianza pero
su ausencia no impide juzgar. Cómo afecta al estado: `review-report`.

| Tipo de diff | Obligatorias | Recomendadas |
| --- | --- | --- |
| Código del backend | `ruff check`, `ruff format --check`, `mypy`, `lint-imports`, `just test-unit` | `just test-integration`; `just mutation` si toca `domain/` o `application/` |
| Migraciones o modelos | `tests/integration/persistence` (deriva y reversibilidad) | `alembic heads` = 1 |
| API, schemas o routers | `tests/unit/contract` | `just test-integration`, `tests/e2e` |
| Workflows o activities de Temporal | `tests/integration/workflows` y `recovery` | test de replay si existe |
| Seguridad (auth, entradas, secretos) | `gitleaks` sobre el diff | `osv-scanner`/`semgrep` si están instalados |
| Frontend | `biome check`, `pnpm test`, `pnpm build` | `pnpm outdated` si cambian dependencias |
| Dockerfile, compose, CI | verificar tags de Actions con `git ls-remote` | `docker build ./backend`; `gh run list --commit` |
| Solo documentación u OpenSpec | `openspec validate <change> --strict` | (ninguna) |
| Mensaje de commit | cabecera ≤ 100 caracteres y tipo válido | (ninguna) |

## 3. Qué buscar en el diff (regresiones)

- **Lo eliminado importa tanto como lo añadido:** una validación, una comprobación o un
  test borrados. `git diff` marca con `-` lo que ya no se hace; pregúntate quién dependía.
- **Cambios de firma o de contrato:** busca los llamadores con `Grep` (también en tests,
  scripts y workflows, que se llaman por nombre de string).
- **Efectos en cascada:** cambio de un puerto → todos sus adaptadores y fakes (`tests/fakes/`).
  Cambio de un modelo → su migración. Cambio de un schema → `docs/openapi.json`.
- **Cambios de comportamiento ocultos en un refactor:** `git diff -w` y compara condiciones,
  orden de operaciones y valores por defecto.
- **Coherencia diff ↔ intención:** cambios que el mensaje no menciona (scope creep) o
  promesas del mensaje que el diff no cumple.
- **Archivos que no deberían estar:** binarios, volcados, `.env`, imágenes sueltas en la
  raíz, salidas de herramientas (`mutants/`, `.coverage`).

## 4. Salida

Devuelve al orquestador: el objetivo revisado, la lista de skills a cargar con el motivo, y
los hallazgos de regresión propios de esta skill ya en el formato de `review-report` (con `skill: diff-review`)
(verificados con `finding-verification`).
