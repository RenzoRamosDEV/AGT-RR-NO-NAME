# Tasks

## 1. Renombrado

- [x] 1.1 Mover el paquete a `backend/src/duelo/`, renombrar `docs/spec/review-arena.md` y
      sustituir el nombre antiguo en archivos versionados (salvo archivo e historia);
      regenerar `uv.lock`; verificar que `grep` no encuentra coincidencias fuera de lo
      excluido.
- [x] 1.2 Regenerar `docs/openapi.json` y verificar `just ci` y `just mutation` en verde.
- [x] 1.3 Cambiar el remoto a `git@github.com:RenzoRamosDEV/Duelo.git` y verificar con
      `git ls-remote origin`.

## 2. Cierre

- [x] 2.1 Commit, push y CI de GitHub en verde; archivar el change.
- [ ] 2.2 Renombrar la carpeta local a `Duelo`, migrar la memoria de Claude Code a la nueva
      ruta y reparar el worktree auxiliar; verificar `git status` y `just test-unit` desde
      la nueva ruta.
