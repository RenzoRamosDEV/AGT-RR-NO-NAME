# Proposal

## Why

Hoy un proyecto solo existe si alguien hace un `insert` a mano en Postgres y los commits solo
llegan si algo llama a `POST /ingest/commit`. Para usar Duelo en local hace falta poder
**añadir un repo desde su carpeta** y que, desde ese momento, **cada commit, push y PR aparezca
solo** en el canal del proyecto.

## What Changes

- Alta de proyectos locales: `POST /projects` con la ruta de un repo git; el slug sale del remoto
  `origin` (`owner/repo`) o del nombre de la carpeta. `DELETE /projects/{slug}` lo da de baja.
- Hooks de git `post-commit` y `pre-push`, instalados en el repo al dar de alta el proyecto, que
  mandan los commits a la API sin bloquear ni retrasar el commit ni el push. Respetan hooks ya
  existentes del usuario (bloque delimitado, idempotente y desinstalable).
- PRs: `POST /projects/{slug}/sync-prs` consulta las PRs abiertas con `gh` y las ingesta como
  `pr`; un sincronizador periódico opcional lo repite para todos los proyectos locales.
- `GET /projects` expone `path`, `hooks_installed` y `github` por proyecto (campos aditivos).
- Todo detrás de `LOCAL_PROJECTS_ENABLED` (apagado por defecto: los endpoints nuevos responden
  404). Variables nuevas: `INGEST_URL`, `PR_SYNC_INTERVAL_SECONDS`.
- CORS admite también `DELETE` (lo necesita el frontend).

## Capabilities

### New Capabilities
- `local-projects`: alta y baja de proyectos desde carpetas locales, hooks de git, sincronización
  de PRs con `gh` y su activación por configuración.

### Modified Capabilities
- `change-queries`: `GET /projects` añade `path`, `hooks_installed` y `github`.
- `api-cors`: el método `DELETE` pasa a estar permitido para los orígenes configurados.

## Impact

- Código: dominio (`Project`, derivación del slug), puertos nuevos (`GitRepository`,
  `HookInstaller`, `GithubPrSource`, `ProjectCatalog`), casos de uso de alta, baja y sincronización,
  adaptadores con `subprocess` (git, gh), instalador de hooks, entrypoint `duelo.entrypoints.hook`
  y routers de proyectos.
- Base de datos: migración `e5b9c2f1a703` (columnas `path`, `hooks_installed`, `github` en
  `projects`).
- Seguridad: la API escribe en `.git/hooks` de rutas que le indica quien tenga el token de
  ingesta; por eso está apagada por defecto y solo tiene sentido con la API corriendo en la
  máquina del usuario (no en contenedor).
- Docs: `docs/architecture.md`, `docs/testing.md`, `README.md`, `docker-compose.yml`,
  `docs/openapi.json`.
