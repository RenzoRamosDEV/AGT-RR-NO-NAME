---
name: dependency-and-config-audit
description: Audita dependencias y configuración - versiones y paquetes obsoletos o vulnerables, lockfiles, scripts de build, Dockerfiles, docker-compose, variables de entorno, workflows de CI/CD y errores de configuración - comprobando compatibilidad antes de recomendar actualizaciones. Úsalo al tocar pyproject.toml, uv.lock, package.json, Dockerfile, compose, .github/ o el justfile.
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(uv tree:*), Bash(uv lock:*), Bash(uv pip:*), Bash(pnpm outdated:*), Bash(pnpm audit:*), Bash(just lint:*), Bash(just ci:*), Bash(gh run list:*), Bash(gh run view:*), Bash(gh api:*), Bash(git ls-remote:*)
---

# Dependencias y configuración

**Comprueba la compatibilidad antes de recomendar una actualización:** lee el changelog o
las notas de la versión, el rango que aceptan los demás paquetes (`uv tree`) y los
mínimos de Python/Node del proyecto (Python `>=3.12,<3.13`; Node 22+). Recomendar `latest`
sin mirar es un hallazgo malo.

## Dependencias

- **Manifiesto y lockfile coherentes:** si cambia `pyproject.toml`, cambia `uv.lock` (y
  viceversa); `pnpm-lock.yaml` con `package.json`. `uv lock --check` lo verifica.
- **Lockfile grande:** no lo leas línea a línea. `uv lock --check` (coherencia) y, para ver
  qué paquetes entran de verdad: `git diff <base> -- uv.lock | grep -E '^[+-]name ='`.
  Revisa solo los paquetes **nuevos** (nombre, mantenedor, necesidad) y los saltos de versión
  mayor; el resto es ruido.
- **Rangos:** límites inferiores realistas (`>=` lo mínimo que se prueba), sin `*`, y sin
  fijar a la versión exacta en librerías salvo motivo.
- **Separación prod/dev:** herramientas de test o lint en el grupo `dev`, nunca en las
  dependencias de ejecución (la imagen de producción se construye con `--no-dev`).
- **Necesidad:** una dependencia nueva para algo que la biblioteca estándar o una ya
  presente resuelven; tamaño, mantenimiento, licencia, y cadena de suministro (typosquatting).
- **Vulnerabilidades y obsolescencia:** `osv-scanner` (CI), `pnpm audit`, `pnpm outdated`.
  Distingue una vulnerabilidad alcanzable por el código de una que no lo es.
- **Renovate** abre PRs de actualización: revísalos con este mismo criterio, no los
  fusiones por inercia.

## Compatibilidad de runtime y pares

Lee los mínimos de los manifiestos, no de memoria: Python (`requires-python` en
`backend/pyproject.toml`), Node y pnpm (`engines`/`packageManager` en
`frontend/package.json`). Una subida de versión mayor exige evidencia: notas de la versión
**y** que pasen los comandos que la ejercitan.
- Frontend: React, Vite, TypeScript, Vitest, jsdom y Testing Library deben ser compatibles
  entre sí (peer dependencies; `pnpm install --frozen-lockfile` no debe avisar de pares
  incumplidos); la prueba es `pnpm build` y `pnpm test`.
- Backend: `temporalio`, `sqlalchemy`, `alembic`, `asyncpg`, `pydantic` y `fastapi` se
  prueban con `just test-integration` (migraciones y Temporal reales), no solo con los unitarios.

## Configuración y entorno

- **Variables de entorno:** las obligatorias fallan rápido con mensaje claro (`INGEST_TOKEN`
  es obligatoria a propósito); toda variable nueva está en `config.py`, documentada y con un
  valor por defecto seguro o ausente. **Todo lugar que arranque la app debe definirla:**
  `docker-compose.yml`, el smoke test del contenedor en CI, el `README`, los tests.
- **Secretos:** nunca valores reales en el repo; en compose, `${VAR:-valor-solo-dev}` con
  comentario de que es solo desarrollo.
- **Puertos y red:** la API se publica en `127.0.0.1`; Postgres y Temporal no deben quedar
  expuestos sin necesidad fuera de local.

## Dockerfile y compose

- Imagen base con versión fijada; build multietapa; `uv sync --frozen --no-dev`.
- Usuario no-root (hay un job que lo comprueba); sin secretos en `ARG`/`ENV`/capas.
- `HEALTHCHECK` que pruebe algo real y coherente con el `CMD` (`uvicorn --factory`).
- `.dockerignore` que excluya `.venv`, `.git`, tests, `mutants/`.
- Pasa `hadolint`.

## CI/CD (`.github/workflows/`)

- **Acciones fijadas por SHA completo** con el tag en comentario; verifica que el tag existe
  con el objeto exacto (`git ls-remote --tags https://github.com/<org>/<repo> <tag>`): un
  prefijo como `@v2` puede no existir, y un `uses:` de workflow reutilizable inválido
  invalida todo el run. Si un workflow es reutilizable, comprueba que declare `workflow_call`.
- **Permisos mínimos:** `permissions:` explícito a nivel de job; nada de `write-all`.
- **Secretos:** no se imprimen, no se exponen a PRs de forks; sin `pull_request_target` que
  haga checkout de código del PR.
- **Coherencia con el local:** lo que corre CI y `just ci` coincide (mismos umbrales,
  mismas variables como `HYPOTHESIS_PROFILE=ci`); un umbral distinto entre ambos es un bug.
- **Tiempo y coste:** timeouts de job, cancelación de runs obsoletos (`concurrency`),
  mutación en el workflow semanal, no en cada push.
- `gh run list` / `gh run view --log-failed` para ver por qué falló el último run.

## Scripts de build y task runner

- El `justfile` es la fuente de verdad de comandos y umbrales (`cov_min`, `cov_core_min`,
  `mutation_min`); no los dupliques en otros sitios sin referenciarlo.
- Recetas con `set -euo pipefail` cuando encadenan comandos; cuidado con globs de `zsh`.
- Podman/Docker: variables `DOCKER_HOST` y `TESTCONTAINERS_RYUK_DISABLED` documentadas.

## Salida

Para cada hallazgo: archivo y línea, el riesgo concreto (qué rompe, cuándo), la versión o
valor correcto con su justificación de compatibilidad, y cómo comprobarlo (`just ci`,
`uv lock --check`, un run de CI).
