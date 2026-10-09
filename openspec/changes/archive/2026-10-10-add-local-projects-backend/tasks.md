# Tasks

## 1. Configuración y dominio

- [x] 1.1 `LOCAL_PROJECTS_ENABLED`, `INGEST_URL`, `PR_SYNC_INTERVAL_SECONDS` y `HOOK_ENV_PATH` en `Settings` con validación; verificar en `test_config.py`
- [x] 1.2 `Project` con `path`, `hooks_installed`, `github` y `slug_for_repository` (https, `git@`, `ssh://`, con y sin `.git`, sin origin, segmentos inválidos); verificar con tests unitarios de partición y límites

## 2. Persistencia

- [x] 2.1 Migración `e5b9c2f1a703` (tras `d4a8e1b5c602`) y `ProjectModel` al día; verificar con los tests de migración up/down y de deriva modelos/esquema
- [x] 2.2 `ProjectCatalog` en el repositorio SQL (alta con conflicto por slug y por ruta, baja con cascada, listado con los campos nuevos); verificar contra Postgres real

## 3. Aplicación

- [x] 3.1 Puertos y excepciones (`GitRepository`, `HookInstaller`, `GithubPrSource`, `ProjectCatalog`) y casos de uso `add_local_project`, `remove_local_project`, `sync_pull_requests` con compensación si fallan los hooks; verificar con fakes (orden, 409, 422, compensación, baja con carpeta ausente, PRs nuevas frente a existentes)

## 4. Adaptadores

- [x] 4.1 `subprocess_runner` sin shell, con plazo y `kill`; verificar con comandos reales (éxito, error, plazo vencido, ejecutable ausente)
- [x] 4.2 `GitRepository` local (raíz, `origin`, enlace simbólico, `..`, subcarpeta, NUL); verificar con repos git temporales reales
- [x] 4.3 `FileHookInstaller` (bloque tras el shebang, hook previo intacto, idempotencia, desinstalación, hook no shell, `core.hooksPath` fuera del repo, worktree, `hook.env` 0600); verificar con repos git temporales reales
- [x] 4.4 `GhPrSource` con `gh` (JSON válido, entradas malformadas, `gh` ausente, sin sesión, plazo); verificar con un `gh` falso en el `PATH`

## 5. Hook

- [x] 5.1 `duelo.entrypoints.hook` (post-commit y pre-push, `fork`, plazo, lectura de `hook.env`, límites de commits y de diff); verificar con repos git reales contra un servidor HTTP local falso: un commit llega con sus campos, push de varios commits sin duplicar, API caída no bloquea ni cambia el código de salida, hook previo y stdin del hook posterior intactos

## 6. API

- [x] 6.1 `POST /projects`, `DELETE /projects/{slug}`, `POST /projects/{slug}/sync-prs`, `path`/`hooks_installed`/`github` en `GET /projects` y `DELETE` en CORS; verificar con tests de API (desactivado 404, 401, 201, 409, 422, 204, 503, límite de peticiones, esquemas)
- [x] 6.2 Sincronizador periódico (`periodic`, `background_jobs`, `lifespan`); verificar con reloj inyectado (repite, sobrevive a un fallo, se cancela al cerrar, apagado con 0)
- [x] 6.3 Composición real y fakes de tests; verificar con un E2E: alta real contra Postgres, commit real con hook y API real, el change aparece en `GET /projects/{slug}/changes`

## 7. Cierre

- [x] 7.1 Regenerar `docs/openapi.json`; actualizar `docs/architecture.md`, `docs/testing.md`, `README.md` y `docker-compose.yml`
- [x] 7.2 `just lint`, `just test`, `just mutation` en verde
