# Review Arena

Web donde cada repo vigilado es un canal al estilo Slack: cada commit o PR dispara una
review en paralelo de Claude Code y Codex, votas a ciegas cuál fue más útil, y un
dashboard compara agentes con datos propios. Ver el spec completo en
[`docs/spec/review-arena.md`](docs/spec/review-arena.md) y las decisiones de arquitectura
en [`docs/adr/`](docs/adr/).

El proyecto se construye de forma incremental con [OpenSpec](https://openspec.dev/):
cada fase del plan de implementación es un *change* en `openspec/changes/`.

## Requisitos

- [`uv`](https://docs.astral.sh/uv/) (gestiona Python 3.12 automáticamente, no hace falta
  instalarlo aparte)
- Node.js 20+ con `pnpm` (vía `corepack enable pnpm`)
- [`just`](https://github.com/casey/just) como task runner
- Un runtime de contenedores compatible con Docker Compose: `docker` + `docker compose`,
  o `podman` + `podman-compose` (este repo usa `podman-compose` por defecto en el
  `justfile`; cambia la variable `compose` si usas `docker compose`)
- [`pre-commit`](https://pre-commit.com/) y [`gitleaks`](https://github.com/gitleaks/gitleaks)
  para los hooks de calidad

## Puesta en marcha

```bash
pre-commit install   # instala los hooks de git (ruff, mypy, biome, gitleaks)
just dev              # levanta Postgres + Temporal + Temporal UI + API
curl localhost:8000/health
just down             # para todo
```

## Comandos habituales

| Comando          | Qué hace                                               |
| ---------------- | ------------------------------------------------------- |
| `just dev`        | Levanta infra (perfil `infra`) + API (perfil `app`)      |
| `just down`       | Para y limpia los contenedores                           |
| `just test`       | Tests de backend (`pytest`) y build de frontend          |
| `just lint`       | Ruff, mypy strict, import-linter y Biome                 |
| `just gen-client` | Genera el cliente TS desde el OpenAPI (desde la Fase 4)  |

## Estructura

Monorepo con arquitectura hexagonal en el backend (`domain` <- `application` <-
`adapters`/`entrypoints`/`workflows`, validado por `import-linter`) y organización por
funcionalidad en el frontend. Ver `docs/architecture.md` para el detalle.
