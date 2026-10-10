# Proposal

## Why

Cuando el usuario deshace un commit (`git reset`, `git commit --amend`, un `rebase`, borrar la rama)
o lo revierte con `git revert`, Duelo sigue mostrándolo como un cambio normal y con su review en
verde: no avisa de que ese código ya no está en la rama. El usuario quiere verlo: la fila en amarillo
y, en el centro, un aviso («commit deshecho» o «commit revertido»).

## What Changes

- **Dos estados nuevos de un commit, además de «activo»**:
  - **Deshecho**: ya no es alcanzable desde ninguna referencia del repositorio local.
  - **Revertido**: otro commit posterior lo invierte (`This reverts commit <sha>`).
  - Si es ambas cosas, gana «deshecho».
- **Detección de deshechos**: tarea periódica de fondo (`REACHABILITY_SWEEP_INTERVAL_SECONDS`, 15 s,
  solo con `LOCAL_PROJECTS_ENABLED`) que pregunta a git qué commits son alcanzables y marca
  `changes.discarded_at` en los que dejaron de serlo (y lo quita si vuelven a serlo).
- **Detección de revertidos**: al ingerir un commit se lee su mensaje (`body`, campo opcional nuevo
  en la ingesta y en el hook) y, si trae `This reverts commit <sha>`, el SHA se guarda en el propio
  commit de revert (`changes.reverts_sha`). El original está revertido mientras exista un revert
  que siga en la rama, así que un revert deshecho (`reset`, `amend`) deja de contar.
- **API (aditiva)**: `commit_state` (`active` | `discarded` | `reverted`) y `reverted_by`
  (`{id, head_sha}`) en el listado y en el detalle; eventos `commit.discarded`, `commit.restored` y
  `commit.reverted` en la línea de tiempo.
- **Interfaz**: la fila de un commit deshecho o revertido se pinta en ámbar, con icono de
  «deshacer» y, en el centro, una etiqueta en mayúsculas con su subtítulo; el detalle muestra un
  aviso equivalente.

## Capabilities

### New Capabilities

- `commit-state`: estados de un commit (activo, deshecho, revertido), su detección y su exposición.

### Modified Capabilities

- `change-ingestion`: campo opcional `body` en `POST /ingest/commit` (y `/ingest/pr`).
- `change-events`: tres tipos de evento nuevos en la lista blanca.
- `frontend-shell`: filas y detalle de commits deshechos o revertidos.

## Impact

Backend (dominio, aplicación, adaptadores de git y de persistencia, composición, API, hook),
migración Alembic, frontend (fila, detalle, mock, tipos) y docs. No se borra ni se altera ninguna
review ni ningún change: el historial se conserva.
