# Proposal

## Por qué

Review Arena todavía no existe como repositorio: no hay monorepo, ni tooling de calidad,
ni CI, ni un servicio que arrancar. Fase 0 del plan de implementación
(`docs/spec/review-arena.md`) exige sentar esa base antes de tocar dominio, Temporal o
frontend, para que la calidad (lint, tipos, tests, CI) esté desde el primer commit y no
se añada al final. Sin esto, cualquier fase posterior no tiene dónde vivir.

## Qué cambia

- Estructura de monorepo con `backend/` (paquete Python hexagonal vacío, listo para
  recibir dominio/aplicación/adaptadores en fases siguientes) y `frontend/` (placeholder
  mínimo, sin features todavía).
- `justfile` con al menos `just dev` (levanta Docker Compose) y `just test`.
- `docker-compose.yml` con perfil `infra` (Postgres, Temporal, Temporal UI) y perfil `app`
  (API) - sin worker `agents`, que nunca corre en Docker.
- `.pre-commit-config.yaml` con Ruff, mypy, Biome y gitleaks.
- CI en GitHub Actions: lint, tipos, build mínimo; falla en rojo si algo no pasa.
- `docs/adr/0001-temporal-vs-alternativas.md`, documentando por qué Temporal frente a
  DBOS/Hatchet/Inngest-Prefect (ya argumentado en el spec general).
- Endpoint `GET /health` en FastAPI (liveness simple, sin dependencias externas todavía).
- `import-linter` configurado con la regla de dependencias
  `domain <- application <- adapters/entrypoints/workflows`, aunque esos paquetes empiecen
  casi vacíos: evita que fases futuras violen la regla desde el primer archivo.

Fuera de esta fase (vienen después, según el plan): dominio real, Temporal workflows,
adaptadores de Postgres/GitHub/agentes, frontend con features, SSE, voto, benchmark.

## Capacidades

### Nuevas capacidades

- `service-health`: el backend expone un endpoint de liveness (`GET /health`) que indica
  si el proceso de la API está vivo. Es una capacidad durable que evolucionará en fases
  posteriores (por ejemplo, un `GET /ready` que además comprueba Postgres y Temporal).

### Capacidades modificadas

(ninguna - no existen specs previos)

## Impacto

- Código nuevo: `backend/` (paquete Python mínimo + `pyproject.toml` con `uv`,
  `src/review_arena/entrypoints/api/` con el router de salud), `frontend/` (placeholder
  Vite), `justfile`, `docker-compose.yml`, `.pre-commit-config.yaml`,
  `.github/workflows/ci.yml`, `docs/adr/0001-temporal-vs-alternativas.md`,
  `.importlinter` (o configuración equivalente en `pyproject.toml`).
- Sin impacto en datos, APIs externas o sistemas de terceros todavía: no hay Postgres con
  esquema real, ni Temporal workflows, ni integraciones con GitHub o agentes en esta fase.
- Done-when (criterio de la Fase 0 en el spec): `just dev` levanta todo el stack y una PR
  vacía pasa la CI en verde.
