# Arquitectura

Monolito modular con tres procesos (API, worker `platform`, worker `agents`) sobre una
arquitectura hexagonal: el dominio (`Change`, `Review`, `Finding`, `Vote`) y los casos de
uso no dependen de Temporal, FastAPI, Postgres ni de los agentes; cada uno de esos es un
adaptador detrás de un puerto. Hoy existe un solo puerto implementado,
`ChangeRepository` (ver `change-ingestion` más abajo); `ReviewAgent`, `CodeHost` y
`EventPublisher` llegarán cuando los changes que los necesiten los introduzcan - no se
diseñan por adelantado. El detalle completo del producto final está en
[`docs/spec/review-arena.md`](spec/review-arena.md).

Este documento indexa las decisiones arquitectónicas registradas como ADR y las
capacidades activas (specs) a medida que se toman/implementan, en vez de repetir aquí lo
que ya está en el spec o en `openspec/specs/`.

## Decisiones registradas (ADR)

- [0001 - Temporal frente a alternativas](adr/0001-temporal-vs-alternativas.md): por qué
  Temporal orquesta las reviews en vez de una cola simple, DBOS, Hatchet, Inngest o
  Prefect.

## Capacidades activas (OpenSpec)

- [`service-health`](../openspec/specs/service-health/spec.md): liveness del proceso de
  la API (Fase 0).
- [`change-ingestion`](../openspec/specs/change-ingestion/spec.md): persistencia atómica
  e idempotente de un `Change` y su evento outbox (Fase 1, primer slice - sin
  `Review`/`Vote`/agentes/Temporal/endpoint HTTP todavía).

## Regla de dependencias (backend)

```
domain  <-  application  <-  adapters / entrypoints / workflows
```

Enforzada por `import-linter` (`backend/pyproject.toml`, sección
`[tool.importlinter]`), validado localmente con `just lint` y en CI.
