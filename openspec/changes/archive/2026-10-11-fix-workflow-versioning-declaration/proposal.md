# Proposal

## Why

El change `temporal-workflow-good-practices` (ya en `main`) declaró
`@workflow.defn(versioning_behavior=VersioningBehavior.AUTO_UPGRADE)` en los dos workflows
apoyándose en una comprobación contra el **servidor de test** (time-skipping), que lo acepta.
El servidor **real** (`auto-setup:1.26.2`, el del compose) rechaza cada activación con
`Client specified an invalid argument: deployment must be set when versioning behavior
specified`: el worker nuevo no completa ningún workflow y las reviews se quedan en marcha para
siempre. Se detectó al reiniciar el worker de desarrollo con el código de `main`.

## What Changes

- Quitar `versioning_behavior` de `ReviewChangeWorkflow` y `ReviewCommitWorkflow`. La semántica
  Auto-Upgrade queda documentada en `docs/adr/0007` y en los comentarios; no se declara al SDK
  mientras no haya Worker Versioning (que es, precisamente, lo que el ADR descarta).
- Corregir el ADR 0007 (decisión 1) y la matriz `docs/temporal-buenas-practicas.md` (WF-6,
  VER-2): la declaración en código solo es posible con `deployment_config`.
- Dejar constancia en `docs/testing.md` de que el servidor de test no reproduce esta validación
  y de que la comprobación contra el servidor real es manual.

## Capabilities

### New Capabilities

### Modified Capabilities

(Sin cambios de comportamiento especificado: la spec `worker-operations` no menciona la
declaración; `skip_specs: true`.)

## Impact

- `backend/src/duelo/workflows/review_change.py`, `review_commit.py`.
- `docs/adr/0007-versionado-de-workflows.md`, `docs/temporal-buenas-practicas.md`,
  `docs/testing.md`.
- Sin cambio de ids, historial ni DTOs: los replay tests siguen igual.
