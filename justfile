compose := "podman-compose"

# Levanta infra (Postgres, Temporal, Temporal UI) + API y espera a que /health responda
dev:
    {{compose}} --profile infra --profile app up -d --build
    @echo "Esperando a que la API responda en /health..."
    @for i in $(seq 1 30); do \
        curl -sf http://localhost:8000/health > /dev/null && echo "API lista." && exit 0; \
        sleep 1; \
    done; \
    echo "La API no respondió a tiempo." >&2; exit 1

# Para y limpia los contenedores levantados por `just dev`
down:
    {{compose}} --profile infra --profile app down

# Corre los tests de backend y frontend
test:
    cd backend && uv run pytest
    cd frontend && pnpm build

# Lint + tipos en todo el repo (mismos checks que corre el CI)
lint:
    cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run lint-imports
    cd frontend && pnpm exec biome check .

# Genera el cliente TypeScript a partir del OpenAPI (placeholder hasta que haya endpoints reales)
gen-client:
    @echo "gen-client: pendiente hasta que exista un contrato OpenAPI que exportar (fase 4)."
