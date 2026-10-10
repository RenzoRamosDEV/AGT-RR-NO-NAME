# Proposal

## Why

La revisión de la PR #12 encontró dos huecos en el marcado de commits deshechos y revertidos:

1. El barrido solo comprobaba `os.path.isdir(path)`, que sigue enlaces simbólicos: si la carpeta
   registrada se sustituye por un enlace a otro repositorio, `git log --all` correría sobre ese
   repositorio (leyendo además su configuración) y marcaría como deshechos commits válidos.
2. Cualquier commit cuyo cuerpo contuviera `This reverts commit <sha>` marcaba como revertido al
   commit con ese SHA, aunque no fuese un `git revert` real.

## What Changes

- **Repositorio revalidado antes de cada consulta**: la ruta no puede ser un enlace simbólico
  (`lstat`) y `git rev-parse --show-toplevel --absolute-git-dir` debe dar la propia carpeta y su
  propio `.git`; si no, `HistoryUnavailable` y no se marca nada.
- **git endurecido** al leer el historial: sin configuración de sistema ni de usuario
  (`GIT_CONFIG_NOSYSTEM`, `GIT_CONFIG_GLOBAL=/dev/null`), `core.fsmonitor=false`,
  `core.hooksPath=/dev/null` y sin `GIT_DIR`/`GIT_WORK_TREE`/`GIT_INDEX_FILE`/`GIT_COMMON_DIR`.
- **Detección de reverts estricta**: solo el formato que escribe `git revert` (título
  `Revert "…"` o `Reapply "…"` y línea exacta `This reverts commit <sha>.` con SHA completo en
  minúsculas de 40 o 64 caracteres). Es lo que declara el mensaje: no se valida el parche inverso.

## Capabilities

### Modified Capabilities

- `commit-state`: barrido (revalidación y git endurecido) y detección de reverts.
