# Tasks

## 1. Estructura del monorepo

- [x] 1.1 Crear la estructura de carpetas raíz (`backend/`, `frontend/`, `docs/adr/`,
      `scripts/`, `prompts/review/`, `e2e/`, `benchmark/`) y un `.gitignore` cubriendo
      Python, Node y artefactos de Docker; verificar con `git status` que no quedan
      directorios vacíos sin `.gitkeep` donde haga falta trackearlos.
- [x] 1.2 Inicializar `backend/pyproject.toml` con `uv` (Python 3.12) y crear el paquete
      `backend/src/review_arena/` con subpaquetes vacíos `domain/`, `application/`,
      `adapters/`, `workflows/`, `entrypoints/` (cada uno con `__init__.py`); verificar
      con `uv run python -c "import review_arena"` que el paquete importa sin error.

## 2. Backend: endpoint de salud (capacidad `service-health`)

- [x] 2.1 Añadir FastAPI y Uvicorn como dependencias en `backend/pyproject.toml` y crear
      `entrypoints/api/app.py` con el router `GET /health` descrito en
      `specs/service-health/spec.md`; verificar levantando `uvicorn` local y haciendo
      `curl localhost:8000/health` → `200 OK`.
- [x] 2.2 Escribir el test que cubre ambos escenarios del spec (`/health` responde 200
      sin Postgres/Temporal configurados) con `pytest` + `httpx.AsyncClient`; verificar
      con `uv run pytest backend/tests/entrypoints/test_health.py -q`.
- [x] 2.3 Configurar `import-linter` (o `ruff`'s equivalente si se prefiere una sola
      herramienta) con la regla `domain <- application <- adapters/entrypoints/workflows`
      en `backend/pyproject.toml`; verificar con `uv run lint-imports` (o el comando
      equivalente) en verde contra el esqueleto actual.

## 3. Frontend: placeholder que compila

- [x] 3.1 Scaffolding de `frontend/` con Vite + React 19 + TypeScript strict (`tsconfig`
      con `strict: true`), sin features todavía, solo una página placeholder; verificar
      con `pnpm --dir frontend build` sin errores de tipos.
- [x] 3.2 Configurar Biome en `frontend/` con la config mínima del proyecto; verificar
      con `pnpm --dir frontend exec biome check .` en verde.

## 4. Docker Compose y `justfile`

- [x] 4.1 Escribir `docker-compose.yml` con perfil `infra` (Postgres, Temporal, Temporal
      UI) y perfil `app` (la API del backend, construida desde `backend/`), sin incluir
      el worker `agents` (ese proceso no corre en Docker, ver `design.md - Decisions`);
      verificar con `docker compose --profile infra config` y `--profile app config` sin
      errores de validación.
- [x] 4.2 Escribir el `justfile` raíz con al menos `just dev` (levanta `infra` + `app` y
      espera a que `/health` responda) y `just test` (corre los tests de backend y
      frontend); verificar ejecutando `just dev` y confirmando `curl localhost:8000/health`
      → `200 OK`, luego `just down`/equivalente para parar los servicios.

## 5. Calidad: pre-commit y gitleaks

- [x] 5.1 Crear `.pre-commit-config.yaml` con hooks de Ruff (lint + format), mypy
      (`--strict` sobre `backend/src`), Biome (sobre `frontend/`) y gitleaks; verificar
      con `pre-commit run --all-files` en verde sobre el estado actual del repo.
- [x] 5.2 Documentar en `README.md` cómo instalar los hooks (`pre-commit install`) y los
      comandos `just` disponibles; verificar que un desarrollador nuevo podría levantar el
      proyecto solo leyendo el README (revisión manual del contenido).

## 6. CI en GitHub Actions

- [x] 6.1 Crear `.github/workflows/ci.yml` con jobs de lint (Ruff, mypy strict, Biome),
      build del frontend y tests de backend (`pytest`, incluyendo el test de `/health`);
      verificar abriendo una PR vacía (sin cambios funcionales) y confirmando que todos
      los jobs terminan en verde.
- [x] 6.2 Añadir el job de `import-linter` al mismo workflow de CI; verificar que falla
      intencionadamente si se introduce un import inverso de prueba (`adapters` ->
      `domain` import extra) y luego revertir ese cambio de prueba.

## 7. Decisión arquitectónica documentada

- [x] 7.1 Escribir `docs/adr/0001-temporal-vs-alternativas.md` siguiendo un formato de
      ADR estándar (contexto, decisión, alternativas consideradas, consecuencias),
      trasladando el análisis Temporal vs. DBOS/Hatchet/Inngest/Prefect de
      `docs/spec/review-arena.md`; verificar que el ADR queda enlazado desde
      `docs/architecture.md` (crear este último si no existe, con un esqueleto mínimo).

## 8. Verificación de integración de la fase

- [x] 8.1 Ejecutar `just dev` desde un checkout limpio y confirmar que Postgres, Temporal,
      Temporal UI y la API quedan arriba y `GET /health` responde `200 OK`; verificar
      también `just test` en verde (backend + frontend) como cierre del criterio
      "hecho cuando" de la Fase 0.

## Workflow follow-up

- Archivar este change con `openspec archive setup-monorepo-foundation` una vez que la PR
  esté revisada y mergeada, para que `specs/service-health/spec.md` pase a ser el spec
  principal del proyecto.
- Verificar tras el archive que `openspec list --specs` muestra `service-health` como
  capacidad activa.
