# Arquitectura

Monolito modular con tres procesos (API, worker `platform`, worker `agents`) sobre una
arquitectura hexagonal: el dominio (`Change`, `Review`, `Finding`, `Vote`) y los casos de
uso no dependen de Temporal, FastAPI, Postgres ni de los agentes; cada uno de esos es un
adaptador detrás de un puerto (`ReviewAgent`, `CodeHost`, `ChangeRepository`,
`EventPublisher`). El detalle completo del diseño está en
[`docs/spec/review-arena.md`](spec/review-arena.md).

Este documento indexa las decisiones arquitectónicas registradas como ADR a medida que
se toman, en vez de repetir aquí lo que ya está en el spec.

## Decisiones registradas (ADR)

- [0001 - Temporal frente a alternativas](adr/0001-temporal-vs-alternativas.md): por qué
  Temporal orquesta las reviews en vez de una cola simple, DBOS, Hatchet, Inngest o
  Prefect.

## Regla de dependencias (backend)

```
domain  <-  application  <-  adapters / entrypoints / workflows
```

Enforzada por `import-linter` (`backend/pyproject.toml`, sección
`[tool.importlinter]`), validado localmente con `just lint` y en CI.
