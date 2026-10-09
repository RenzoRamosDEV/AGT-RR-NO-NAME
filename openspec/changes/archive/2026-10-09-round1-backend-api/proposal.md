# Proposal

## Por qué

El frontend sigue trabajando con datos de ejemplo (`frontend/src/data/mock.ts`) porque la
API solo sabe ingerir commits: no hay forma de listar proyectos, leer el canal de un
proyecto, abrir un change con sus reviews ni comparar agentes. La ronda 1 de propuestas de
Codex señaló cinco huecos de backend que, juntos, dejan la API lista para que la interfaz
deje de usar mocks, y que reutilizan casi todo lo que ya existe (modelos, índices y
`ChangeKind.PR`).

## Qué cambia

- **`GET /projects`**: lista los proyectos vigilados (`id`, `slug`) ordenados por slug.
- **`GET /projects/{slug}/changes`**: canal de un proyecto, del más reciente al más antiguo,
  con filtro `kind` (`commit`/`pr`), `limit` (1-100, 50 por defecto) y paginación por cursor
  opaco (`next_cursor`). Los elementos no llevan el diff: un canal de 100 changes no debe
  mover decenas de MB. Proyecto desconocido: 404.
- **`GET /changes/{id}`**: detalle de un change con su diff y las reviews ya registradas
  (completadas y fallidas), sin la salida cruda del agente. Inexistente: 404.
- **`POST /ingest/pr`**: igual que `POST /ingest/commit` pero para `ChangeKind.PR`, con el
  mismo token, validaciones, recorte de diff e idempotencia (identidad natural: proyecto,
  `kind`, `head_sha`). El workflow id incluye el `kind` para que un PR y un commit con el
  mismo sha no se pisen.
- **`GET /stats/agents`**: métricas agregadas por agente (reviews totales, completadas,
  fallidas, duración media y score medio).

Fuera de este change: autenticación de las lecturas (ver `design.md`), webhooks de GitHub,
debounce de PRs, SSE, filtros por proyecto en las estadísticas y cualquier cambio en el
frontend (cliente generado incluido).

## Capacidades

### Nuevas capacidades

- `change-queries`: un cliente puede listar proyectos, leer el canal paginado de un proyecto,
  abrir un change con sus reviews y consultar métricas por agente.
- `pr-ingestion`: un cliente autenticado puede enviar un PR y el sistema lo persiste y
  dispara su review sin duplicar trabajo.

### Capacidades modificadas

(ninguna: `commit-ingestion` no cambia de comportamiento observable)

## Impacto

- Backend: `application/` (puertos `ProjectRepository.list_all`,
  `ChangeRepository.list_for_project`, `ReviewRepository.list_for_change` y `agent_stats`;
  `read_models.py`; casos de uso `ingest_pr`, `list_projects`, `list_changes`,
  `get_change_detail`, `agent_stats`), `adapters/persistence/` (consultas), `adapters/orchestration/`
  (workflow id con `kind`), `entrypoints/api/` (tres routers nuevos, schemas, cursor,
  `ApiDependencies`), `composition.py`, `docs/openapi.json`.
- Sin migración de esquema: `ix_changes_project_created_at` ya cubre el canal.
- Contrato: endpoints nuevos y esquemas nuevos; los existentes no cambian.
