# Design

## Credenciales: solo el fichero

`load_config(env_path)` pasa a leer únicamente el fichero `KEY=VALUE` (`INGEST_URL`,
`INGEST_TOKEN`). Se elimina el `os.environ.get(...)` que tenía prioridad. Razón: el entorno de un
`git commit` lo controla quien lo lanza, y el fichero (modo 0600 en un directorio 0700) es lo único
que debe poder decidir a dónde viaja el token. Los tests que antes inyectaban `INGEST_URL`/`INGEST_TOKEN`
por entorno escriben ahora un fichero y lo pasan con `--env-file` (el mismo mecanismo que usan los
hooks reales: no hay un atajo «solo para tests» que exista también en producción).

La URL se valida con `urllib.parse`: esquema `http`/`https` y host no vacío; si no, no hay
configuración y no se envía nada (el token tampoco).

## Ruta del fichero en el bloque

`render_block` recibe `env_path` y añade `--env-file '<ruta>'` a la orden. La ruta la fija el
instalador (`FileHookInstaller._env_path`, de `HOOK_ENV_PATH` o el valor por defecto), se entrecomilla
con comillas simples y no contiene datos del repo ni del commit. En `main`, `--env-file` es opcional:
sin él se usa `default_env_path()` (hooks instalados antes de este change). La ruta se resuelve a
absoluta al instalar para que no dependa del directorio desde el que corra git.

## Baja: primero los hooks

`remove_local_project` busca el proyecto (`catalog.get_by_slug`), desinstala los hooks si tiene
carpeta y solo después borra. Si `hooks.uninstall` lanza `HookInstallError` u `OSError`, el caso de
uso lanza `HookRemovalFailed` y el proyecto queda intacto; el router lo traduce a 409 con un `detail`
accionable («No se pudieron quitar los hooks de …: corrige los permisos de .git/hooks y repite la
baja»). `uninstall` ya trata como éxito una carpeta inexistente o sin hooks reconocibles. La carrera
(dos bajas a la vez) se resuelve igual que antes: el borrado devuelve `None` a quien llega segundo y
ese recibe 404.

## Alternativas descartadas

- Mantener el override de entorno pero ignorarlo si la URL difiere del fichero: más complejo y deja
  la puerta abierta a otros campos.
- Un estado «pendiente de limpieza» en la tabla de proyectos: añade migración y UI; con el orden
  correcto (desinstalar primero) el estado intermedio no existe.
