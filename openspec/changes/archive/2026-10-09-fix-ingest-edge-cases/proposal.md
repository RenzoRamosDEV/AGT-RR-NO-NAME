# Proposal

## Por qué

La primera revisión real de `code-guardian` sobre `ef2ceec` (ingesta de commits) encontró dos
defectos de comportamiento que ningún test cubría, ambos verificados:

1. **500 en vez de 422 con NUL en `project`.** El dominio rechaza `\x00` en `head_sha`, `ref`
   y `url`, pero `project` (el slug) llega tal cual a la consulta de Postgres, que lanza
   `invalid byte sequence for encoding "UTF8": 0x00`. Con token válido, la API responde 500.
2. **Un commit ya revisado relanza su review.** `start_workflow` no fija `id_reuse_policy`,
   y el valor por defecto de Temporal (`ALLOW_DUPLICATE`) permite reutilizar el workflow id
   cuando la ejecución anterior ya terminó. Reenviar el mismo commit volvería a llamar a los
   agentes (con agentes reales: coste y tiempo), contra el requisito de "sin duplicar
   trabajo". Las filas de `reviews` no se duplican gracias a `ON CONFLICT`, por eso nada lo
   detectó.

## Qué cambia

- `project` rechaza NUL en el schema de la API (422 sin efectos), y el repositorio de
  proyectos trata un slug con NUL como inexistente en vez de consultar la base de datos.
- `TemporalReviewStarter` arranca con `WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY`:
  un commit con review completada no se relanza, pero uno cuyo workflow falló o se canceló
  sí puede reintentarse reenviándolo.
- Delta de spec con ambos comportamientos y tests que los fijan.

## Capacidades

### Nuevas capacidades

Ninguna.

### Capacidades modificadas

- `commit-ingestion`: dos requisitos nuevos (entrada inválida sin efectos y reingesta tras
  completar la review).

## Impacto

- `entrypoints/api/schemas.py`, `adapters/persistence/project_repository.py`,
  `adapters/orchestration/temporal_review_starter.py`; sin migraciones. El snapshot
  `docs/openapi.json` no cambia si el validador no altera el schema generado (se comprueba).
