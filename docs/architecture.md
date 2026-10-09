# Arquitectura

Monolito modular con tres procesos (API, worker `platform`, worker `agents`) sobre una
arquitectura hexagonal: el dominio (`Change`, `Review`, `Finding`, `Vote`) y los casos de
uso no dependen de Temporal, FastAPI, Postgres ni de los agentes; cada uno de esos es un
adaptador detrás de un puerto. Hoy existe un solo puerto implementado,
`ChangeRepository` (ver `change-ingestion` más abajo); `ReviewAgent`, `CodeHost` y
`EventPublisher` llegarán cuando los changes que los necesiten los introduzcan - no se
diseñan por adelantado. El detalle completo del producto final está en
[`docs/spec/duelo.md`](spec/duelo.md).

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
  e idempotente de un `Change` y su evento outbox, con límites de campo, recorte de
  metadatos y saneado de NUL (Fase 1).
- [`change-review`](../openspec/specs/change-review/spec.md): reviews en paralelo con
  `FakeAgent` mediante workflows de Temporal, tolerantes a fallos parciales, atómicas e
  idempotentes por `(change, agent, run)` (Fase 2, primer slice).
- [`commit-ingestion`](../openspec/specs/commit-ingestion/spec.md):
  `POST /ingest/commit` autenticado con token de ingesta; persiste el commit y arranca su
  review sin duplicar trabajo; `GET /ready` comprueba Postgres y Temporal (Fase 2, cierre).
  Contrato OpenAPI en [`openapi.json`](openapi.json).
- `change-queries` y `pr-ingestion` (change `round1-backend-api`): lecturas sin token
  (`GET /projects`, `GET /projects/{slug}/changes` con cursor, `GET /changes/{id}`,
  `GET /stats/agents`; ver la decisión sobre autenticación de lecturas en su `design.md`) y
  `POST /ingest/pr` con la misma identidad idempotente que los commits.

## Calidad y tests

- [Estrategia de tests](testing.md): capas unit/integration, mutation testing, umbrales de
  cobertura y el mapa de cada tipo de test (cubierto / diferido con motivo).

## Regla de dependencias (backend)

```
domain  <-  application  <-  adapters / entrypoints / workflows
```

La única pieza que conoce a la vez `entrypoints`, `adapters` y `workflows` es la raíz de
composición (`duelo/composition.py` para la API y `duelo/worker.py` para el
worker de desarrollo); queda fuera de las capas a propósito.

Enforzada por `import-linter` (`backend/pyproject.toml`, sección
`[tool.importlinter]`), validado localmente con `just lint` y en CI.
