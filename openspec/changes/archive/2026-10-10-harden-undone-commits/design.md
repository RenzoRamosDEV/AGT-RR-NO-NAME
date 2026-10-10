# Design

- **Identidad del repositorio**: `lstat` (no sigue enlaces) + `rev-parse --show-toplevel
  --absolute-git-dir` con `realpath` de ambos. Cubre el enlace, una subcarpeta, otro repositorio y
  un `.git` que es un archivo `gitdir:` hacia otro. Un worktree enlazado (su `.git` es un archivo)
  deja de barrerse: es el lado seguro (no se marca nada).
- Se hace en CADA consulta (`reachable` y `contains`): una llamada extra a git por consulta.
- **git**: el mismo `run_command` (sin shell, con plazo) con `env` y `-c` endurecidos. El resto del
  entorno heredado se mantiene (PATH, HOME para ejecutar git).
- **Formato de revert**: se aceptan también los mensajes de reverts de fusiones
  (`This reverts commit <sha>, reversing\nchanges made to <sha>.`) y de reverts de reverts
  (`Reapply "…"`), verificados con `git revert` real. Un mensaje escrito a mano con ese formato
  exacto se acepta: es una declaración del mensaje, no una prueba.
