# Design

## Context

Ver `proposal.md`. `temporalio` 1.34 acepta `versioning_behavior` en `@workflow.defn` sin
`deployment_config` y lo envía en cada `RespondWorkflowTaskCompleted`; el servidor de test
(`start_time_skipping`) lo ignora, el servidor real 1.26.2 lo valida y lo rechaza si el worker no
está registrado en un *Worker Deployment*. No hay CLI `temporal` instalada con la que levantar un
`server start-dev` en los tests.

## Goals / Non-Goals

**Goals:** que el worker vuelva a completar workflows contra el servidor real sin perder la
decisión de versionado documentada.

**Non-Goals:** adoptar Worker Versioning o un `deployment_config`; añadir un servidor real a la
suite (no hay binario `temporal` ni Docker en los tests unitarios; el de integración ya usa
testcontainers para Postgres y podría usar la imagen `auto-setup`, pero es un cambio aparte).

## Decisions

1. **Quitar la declaración**, no añadir `deployment_config`. Un `deployment_config` activaría
   Worker Versioning, que el ADR 0007 descarta porque Duelo tiene un worker por cola.
2. **La semántica vive en el ADR y en un comentario** junto a cada `@workflow.defn`, con el
   mensaje exacto del servidor para que nadie lo vuelva a «mejorar».
3. **Sin test automático nuevo**: el único que lo detectaría es un servidor real. Se documenta
   como comprobación manual en `docs/testing.md` (fila de operación del worker) y el ADR exige
   validar contra `just dev` cualquier opción nueva de `@workflow.defn` o del `Worker`.

## Risks / Trade-offs

- [Volver a introducir una opción que el servidor de test tolera y el real no] → regla en el ADR
  y comentario en el código; a medio plazo, un test de integración con la imagen
  `temporalio/auto-setup` en testcontainers.
