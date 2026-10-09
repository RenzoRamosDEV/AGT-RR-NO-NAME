compose := "podman-compose"

# Levanta infra (Postgres, Temporal, Temporal UI) + API y espera a que /health responda
dev:
    {{compose}} --profile infra --profile app up -d --build
    @echo "Esperando a que la API responda en /health..."
    @for _ in $(seq 1 30); do \
        curl -sf http://localhost:8000/health > /dev/null && echo "API lista." && exit 0; \
        sleep 1; \
    done; \
    echo "La API no respondió a tiempo." >&2; exit 1

# Para y limpia los contenedores levantados por `just dev`
down:
    {{compose}} --profile infra --profile app down

# Aplica las migraciones de Alembic a la base de datos local (DATABASE_URL o la de compose)
migrate:
    cd backend && uv run alembic upgrade head

# Worker de desarrollo (task queues platform y agents, con FakeAgent) contra la infra local
worker:
    cd backend && uv run python -m duelo.worker

# Regenera el snapshot del contrato (docs/openapi.json) tras un cambio deliberado de la API
openapi:
    cd backend && PYTHONPATH=. uv run python ../scripts/dump_openapi.py

# Carga ligera de POST /ingest/commit (bajo demanda; requiere API + worker + infra arriba)
load *args:
    cd backend && uv run python ../scripts/load_ingest.py {{args}}

# Tests unitarios: sin Docker, sin red, milisegundos
test-unit:
    cd backend && uv run pytest tests/unit -m unit --no-cov

# Umbrales de cobertura de líneas+ramas (%): global y para domain+application (lógica pura)
cov_min := "97"
cov_core_min := "100"

# Tests de integración: Postgres real (testcontainers) y Temporal de test; necesitan Docker o Podman
test-integration:
    #!/usr/bin/env bash
    set -euo pipefail
    cd backend
    if ! command -v docker >/dev/null 2>&1; then
        # Sin `docker` (p. ej. Podman-only): apuntar testcontainers al socket de Podman
        # y desactivar Ryuk, su sidecar de limpieza, que no funciona bien en rootless.
        export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
        export TESTCONTAINERS_RYUK_DISABLED=true
    fi
    uv run pytest tests/integration -m integration --no-cov

# Toda la suite con cobertura de ramas y umbrales, más el build del frontend
test:
    #!/usr/bin/env bash
    set -euo pipefail
    cd backend
    if ! command -v docker >/dev/null 2>&1; then
        export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
        export TESTCONTAINERS_RYUK_DISABLED=true
    fi
    uv run pytest
    core="src/duelo/domain/*,src/duelo/application/*"
    echo "cobertura (líneas+ramas): global $(uv run coverage report --format=total)% (mín {{cov_min}}%)," \
         "domain+application $(uv run coverage report --include="$core" --format=total)% (mín {{cov_core_min}}%)"
    uv run coverage report --fail-under={{cov_min}} >/dev/null \
        || { echo "FALLA: cobertura global por debajo de {{cov_min}}%" >&2; exit 1; }
    uv run coverage report --include="$core" --fail-under={{cov_core_min}} >/dev/null \
        || { echo "FALLA: cobertura de domain+application por debajo de {{cov_core_min}}%" >&2; exit 1; }
    cd ../frontend && pnpm build

# Lint + tipos en todo el repo (mismos checks que corre el CI)
lint:
    cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run lint-imports
    cd frontend && pnpm exec biome check .

# Genera el cliente TypeScript a partir del OpenAPI (placeholder hasta que haya endpoints reales)
gen-client:
    @echo "gen-client: pendiente hasta que exista un contrato OpenAPI que exportar (fase 4)."

# Reproduce localmente lo que corre el CI (sin gitleaks/osv-scanner/hadolint, que necesitan sus binarios aparte)
ci: lint test
    {{compose}} --profile infra config
    {{compose}} --profile app config

# Umbral mínimo de puntuación de mutación (%) sobre domain/ y application/
mutation_min := "95"

# Mutation testing sobre domain/ y application/ (unos segundos); falla bajo el umbral
mutation:
    #!/usr/bin/env bash
    set -euo pipefail
    cd backend
    rm -rf mutants
    uv run mutmut run 2>&1 | tr '\r' '\n' | grep -E "mutations/second|^[0-9]+/[0-9]+ " | tail -2 || true
    uv run mutmut export-cicd-stats >/dev/null
    uv run python ../scripts/mutation_gate.py mutants/mutmut-cicd-stats.json --min {{mutation_min}}
