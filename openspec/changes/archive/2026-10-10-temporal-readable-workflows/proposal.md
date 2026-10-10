# Proposal

## Why

Al abrir la interfaz de Temporal el usuario ve workflows llamados `commit-<uuid del proyecto>-<sha de 40>`
y `review-<uuid del change>-r1`, y al abrir una actividad solo ve `{status, review_id}`. No se sabe de
qué repositorio es cada uno ni si es un commit o una PR, y **no se puede leer lo que respondió el
reviewer** (resumen, nota, hallazgos) sin ir a la base de datos o a la UI de Duelo.

## What Changes

- **Respuesta del reviewer visible en Temporal.** El resultado de la activity `run_review` (y con él
  el evento `ActivityTaskCompleted` y los resultados del hijo y del padre) lleva el agente, el
  resumen, la nota, los hallazgos y el error saneado, **acotados** y sin la salida cruda del CLI. El
  workflow hijo muestra en «Current Details» (markdown) una línea por agente que se rellena según
  terminan, y cada actividad lleva un resumen de una línea («claude revisa 3f2a9c1»).
- **Nombres legibles.** Los ids pasan a `{kind}-{repo}-{sha12}-{proyecto6}[-r{run}]` y
  `review-{kind}-{repo}-{sha12}-{proyecto6}-r{run}` (por ejemplo `commit-acme-widgets-3f2a9c1b7d4e-ab12cd`,
  `pr-acme-widgets-…`, `review-commit-acme-widgets-…-r1`). El sufijo de 6 hex sale del UUID del proyecto: sin
  él, quitar un proyecto y volver a añadirlo con el mismo nombre haría que Temporal ignorase en
  silencio el commit repetido. Los workflows llevan además un resumen estático («commit ·
  acme/widgets · título») que la UI de Temporal muestra en la lista.
- **Sin relanzar agentes por el cambio de id.** Antes de arrancar con el id nuevo, el starter
  consulta también el id antiguo: si esa ejecución existe y no falló, no arranca otra (reenviar un
  commit ya revisado no vuelve a gastar la suscripción del usuario).
- **Compatibilidad.** El id y los metadatos del hijo se calculan dentro del workflow: van tras
  `workflow.patched("readable-workflow-names")`, de modo que las ejecuciones en vuelo se reproducen
  con su id antiguo. Los workflows terminados conservan su nombre.

## Capabilities

### New Capabilities
- `workflow-observability`: nombres, resúmenes y respuestas de los reviewers visibles en Temporal.

## Impact

- Código: `workflows/{dto,review_change,review_commit,activities}.py`,
  `application/{review_requests,workflow_naming,review_summary}.py`,
  `adapters/orchestration/temporal_review_starter.py`, `adapters/persistence/project_repository.py`
  (`slug_of`), puerto `ProjectSlugs`, composición.
- Temporal: los payloads de resultado crecen (acotados). El texto de las reviews, que puede citar
  código, queda en el historial de Temporal local. Posible subida del servidor del compose para
  mostrar los metadatos de usuario (ver `design.md`).
- API, base de datos y frontend: sin cambios.
- Docs: `README.md`, `docs/architecture.md`, `docs/testing.md`, `docs/flujo-duelo.html`.
