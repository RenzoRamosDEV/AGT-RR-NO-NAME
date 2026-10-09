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

# Tests unitarios: sin Docker, sin red, milisegundos
test-unit:
    cd backend && uv run pytest tests/unit -m unit --no-cov

# Tests de integración: Postgres real (testcontainers) y Temporal de test; necesitan Docker o Podman
test-integration:
    #!/usr/bin/env bash
    set -euo pipefail
    cd backend
    if command -v docker >/dev/null 2>&1; then
        uv run pytest tests/integration -m integration --no-cov
    else
        # Sin `docker` (p. ej. Podman-only): apuntar testcontainers al socket de Podman
        # y desactivar Ryuk, su sidecar de limpieza, que no funciona bien en rootless.
        DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock" \
        TESTCONTAINERS_RYUK_DISABLED=true \
        uv run pytest tests/integration -m integration --no-cov
    fi

# Toda la suite con cobertura (unit + integration) y build del frontend
test:
    #!/usr/bin/env bash
    set -euo pipefail
    cd backend
    if command -v docker >/dev/null 2>&1; then
        uv run pytest
    else
        DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock" \
        TESTCONTAINERS_RYUK_DISABLED=true \
        uv run pytest
    fi
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
