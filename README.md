# Duelo

Web donde cada repo vigilado es un canal al estilo Slack: cada commit o PR dispara una
review en paralelo de Claude Code y Codex, votas a ciegas cuál fue más útil, y un
dashboard compara agentes con datos propios. Ver el spec completo en
[`docs/spec/duelo.md`](docs/spec/duelo.md) y las decisiones de arquitectura
en [`docs/adr/`](docs/adr/).

El proyecto se construye de forma incremental con [OpenSpec](https://openspec.dev/):
cada fase del plan de implementación es un *change* en `openspec/changes/`.

## Requisitos

- [`uv`](https://docs.astral.sh/uv/) (gestiona Python 3.12 automáticamente, no hace falta
  instalarlo aparte)
- Node.js 22+ con `pnpm` (vía `corepack enable pnpm`) - misma versión que usa el CI
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

### Probar la ingesta de un commit

```bash
export INGEST_TOKEN=dev-ingest-token       # solo desarrollo local
just dev                                  # infra + API (usa INGEST_TOKEN)
just migrate                              # esquema de la base de datos
just worker                               # worker con agentes de prueba (otra terminal)
# un proyecto de prueba (la creación por API llega con el slice de Project):
podman exec -i <contenedor-postgres> psql -U duelo -c \
  "insert into projects(id, slug) values (gen_random_uuid(), 'demo/repo')"
curl -i -X POST localhost:8000/ingest/commit \
  -H "X-Ingest-Token: $INGEST_TOKEN" -H 'content-type: application/json' \
  -d '{"project":"demo/repo","ref":"refs/heads/main","head_sha":"abc123","title":"t","author":"yo","diff":"d"}'
# -> 202 con el change_id; en la Temporal UI (localhost:8080) aparece commit-<proyecto>-abc123
#    y la tabla reviews acaba con una fila completed por agente
curl localhost:8000/ready                 # 200 solo si Postgres y Temporal responden
```

El token es un secreto compartido (`INGEST_TOKEN`); la API escucha solo en `127.0.0.1`.

### Revisar de verdad con Claude Code y Codex

Por defecto `AGENT_NAMES=agent_1,agent_2`: son agentes de prueba (`FakeAgent`) que devuelven siempre
la misma review. Para que revisen los CLI **reales** de tu terminal, **sin claves de API** (usan la
sesión que ya tienes iniciada), arranca la API **y** el worker con la misma lista:

```bash
export AGENT_NAMES=claude,codex          # en la API y en el worker
just worker                              # en TU máquina: ahí están los CLI con la sesión iniciada
```

Requisitos y garantías:

- `claude` y `codex` instalados y con sesión iniciada (`claude` y `codex login`). Si no hay sesión o no
  están en el `PATH`, la review queda `failed` con un mensaje claro y se puede reintentar.
- **Solo lectura y confinados:** Claude Code recibe únicamente `Read`, `Grep` y `Glob`, en modo
  `--restricted` (sus herramientas de fichero quedan confinadas a su directorio de trabajo) y sin poder
  pedir permisos. Codex corre con el sandbox `read-only`, sin tu configuración ni tus reglas y con las
  herramientas de shell, navegador, aplicaciones, plugins e imágenes **desactivadas** (con solo
  `read-only` un prompt «ejecuta `cat /etc/hostname`» sí devolvía el contenido; con esto no). Ninguno
  carga tus MCP ni tus hooks. Nada de Bash, Edit, Write ni red.
- El diff (hasta 60 000 caracteres) viaja por la entrada estándar, no por argumentos, y se trata como
  **dato no confiable**: el prompt ordena ignorar cualquier instrucción que contenga.
- **Claude** lee la carpeta del proyecto (si se añadió desde una carpeta local; si no, un directorio
  temporal vacío) para dar contexto, solo lectura. **Codex revisa solo el diff**: sin herramienta de
  shell no puede leer ficheros, así que trabaja siempre en un directorio temporal vacío y no se le
  expone tu repositorio.
- **Riesgo residual de Codex:** la lista de funciones desactivadas es de denegación; una versión
  futura de Codex con una herramienta nueva que leyera el disco no estaría desactivada. Lo acotan el
  sandbox `read-only` (sin escritura ni red), el directorio temporal vacío, el entorno sin secretos
  y los tests opcionales con el CLI real (`RUN_CLI_AGENT_TESTS=1`), que comprueban que no puede
  ejecutar ni leer fuera. Tras un fallo de plazo, un proceso que el CLI hubiera desasociado puede
  seguir vivo (se abandona su espera, pero no se le mata).
- Al proceso del CLI **no** llegan `INGEST_TOKEN`, `OPERATOR_TOKEN`, `DATABASE_URL` ni tus claves
  `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` (si las tuvieras en el entorno, el CLI las usaría en lugar de tu
  sesión).
- **Consumo:** cada review gasta tu suscripción (una review de un diff diminuto: ≈ 0,03 USD de lista en
  Claude y ≈ 13 000 tokens en Codex; más con diffs grandes). `AGENT_MAX_CONCURRENCY` (2) limita cuántos
  CLI corren a la vez.
- La calidad depende del modelo: la nota y los hallazgos no se verifican contra el código.

| Variable (worker) | Por defecto | Qué hace |
| --- | --- | --- |
| `AGENT_NAMES` | `agent_1,agent_2` | `claude` y `codex` usan los CLI reales; cualquier otro nombre, el agente de prueba |
| `AGENT_TIMEOUT_SECONDS` | `240` | Plazo de cada ejecución del CLI. Máximo 270: la activity dura 5 minutos y se reservan 30 s para limpiar y guardar la review fallida |
| `AGENT_MAX_CONCURRENCY` | `2` | CLI simultáneos en este worker; el resto espera en la cola de Temporal |
| `CLAUDE_BIN` / `CODEX_BIN` | en el `PATH` | Ruta del ejecutable si no está en el `PATH` |
| `CLAUDE_MODEL` / `CODEX_MODEL` | el del CLI | Modelo a usar |
| `CLAUDE_MAX_BUDGET_USD` | `2` | Tope de gasto (USD de lista) de una ejecución de Claude Code |

### Variables de entorno de la API

| Variable | Por defecto | Qué hace |
| --- | --- | --- |
| `INGEST_TOKEN` | (obligatoria) | Token de ingesta y de reintento de reviews |
| `OPERATOR_TOKEN` | sin configurar | Descarga de la salida cruda de una review (`X-Operator-Token`); distinto de `INGEST_TOKEN`, 16+ caracteres |
| `MAX_INGEST_BODY_BYTES` | `1500000` | Tamaño máximo del cuerpo de `POST /ingest/commit` y `/ingest/pr` (413 si lo supera); el diff además se trunca a `MAX_DIFF_CHARS` |
| `ALLOWED_ORIGINS` | vacía (sin CORS) | Orígenes del navegador permitidos, separados por comas (`http://localhost:5173`); no admite `*` |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | `300` / `60` | Límite por IP de `POST /ingest/*` y `/changes/{id}/retry` (429 con `Retry-After`); `0` lo desactiva. Es en memoria de un proceso |
| `STALE_AFTER_SECONDS` | `1800` | Un change `pending`/`running` cuyo `run` actual empezó hace más se marca `stale` (solo diagnóstico) |
| `LOCAL_PROJECTS_ENABLED` | `false` | Habilita añadir proyectos desde carpetas locales (instala hooks de git). Solo con la API en tu máquina, no en contenedor; apagado, esos endpoints dan 404 |
| `INGEST_URL` | `http://127.0.0.1:8000` | Dónde envían los hooks los commits (ajústala si usas otro puerto) |
| `HOOK_ENV_PATH` | `~/.config/duelo/hook.env` | Fichero 0600 con la URL y el token que leen los hooks |
| `PR_SYNC_INTERVAL_SECONDS` | `0` | Sincronización periódica de PRs con `gh` (`0` = solo bajo demanda) |

### Proyectos desde carpetas locales

Con la API corriendo **en tu máquina** (no en el contenedor) y `LOCAL_PROJECTS_ENABLED=true`:

```bash
export INGEST_TOKEN=dev-ingest-token LOCAL_PROJECTS_ENABLED=true INGEST_URL=http://127.0.0.1:8001
cd backend && uv run uvicorn --factory duelo.composition:create_app_from_env --port 8001
# dar de alta un repo (raíz de un repo git): instala los hooks post-commit y pre-push
curl -X POST localhost:8001/projects -H "X-Ingest-Token: $INGEST_TOKEN" \
  -H 'content-type: application/json' -d '{"path": "/ruta/absoluta/a/tu/repo"}'
# a partir de ahora cada commit y push de ese repo aparece solo en su canal
curl -X POST localhost:8001/projects/owner/repo/sync-prs -H "X-Ingest-Token: $INGEST_TOKEN"  # PRs con `gh`
curl -X DELETE localhost:8001/projects/owner/repo -H "X-Ingest-Token: $INGEST_TOKEN"        # baja y quita los hooks
```

Los hooks no bloquean ni retrasan `git commit` ni `git push` (envían en segundo plano y salen con
código 0 aunque la API esté caída) y respetan tus propios hooks: Duelo solo añade un bloque entre
`# >>> duelo >>>` y `# <<< duelo <<<`, que la baja retira. El token se guarda en
`~/.config/duelo/hook.env` (0600, o en `HOOK_ENV_PATH`), nunca en el repo. Los hooks leen la URL y
el token **solo de ese fichero**: un `INGEST_URL=... git commit` del entorno se ignora. Si la baja no
puede quitar los hooks (p. ej. `.git/hooks` sin permiso de escritura) responde 409 y conserva el
proyecto para repetirla. Quien tenga el token puede hacer que la API escriba hooks en tus repos: no
actives esto en un servidor compartido ni expongas la API.

Cada respuesta lleva `X-Request-ID` (se propaga el entrante si es válido) y la API escribe un
access log JSON por petición en stdout, sin query, cuerpo ni tokens.

## Comandos habituales

| Comando          | Qué hace                                               |
| ---------------- | ------------------------------------------------------- |
| `just dev`        | Levanta infra (perfil `infra`) + API (perfil `app`)      |
| `just down`       | Para y limpia los contenedores                           |
| `just migrate`    | Aplica las migraciones de Alembic                        |
| `just worker`     | Worker de desarrollo (`platform` + `agents`; `AGENT_NAMES=claude,codex` usa los CLI) |
| `just load`       | Carga ligera de `POST /ingest/commit` (bajo demanda)     |
| `just openapi`    | Regenera el snapshot `docs/openapi.json`                 |
| `just test`       | Tests de backend (`pytest`) y build de frontend          |
| `just lint`       | Ruff, mypy strict, import-linter y Biome                 |
| `just gen-client` | Genera el cliente TS desde el OpenAPI (desde la Fase 4)  |

## Estructura

Monorepo con arquitectura hexagonal en el backend (`domain` <- `application` <-
`adapters`/`entrypoints`/`workflows`, validado por `import-linter`) y organización por
funcionalidad en el frontend. Ver `docs/architecture.md` para el detalle.

**Guía interactiva del flujo:** [`docs/flujo-duelo.html`](docs/flujo-duelo.html) explica de punta
a punta cómo funciona Duelo (hook de git, API, Postgres, Temporal, workers y frontend) con un
simulador animado y las limitaciones reales. Es un solo archivo: ábrelo en el navegador.
