# Proposal

## Por qué

El proyecto tenía el nombre provisional "Review Arena" y el repositorio se ha renombrado a
`Duelo` (`github.com/RenzoRamosDEV/Duelo`). El nombre antiguo sigue en el paquete Python, los
imports, la configuración, la documentación, la interfaz y el remoto de git local, que aún
apunta al nombre anterior del repositorio (`AGT-RR-NO-NAME`, que GitHub redirige).

## Qué cambia

- Remoto `origin` → `git@github.com:RenzoRamosDEV/Duelo.git`.
- Paquete Python `review_arena` → `duelo` (directorio `backend/src/duelo/`, todos los
  imports, `import-linter`, `mutmut`, `alembic`, `Dockerfile`, `uvicorn --factory`) y nombre
  de distribución `review-arena` → `duelo` (`pyproject.toml`, `uv.lock`).
- Credenciales y nombre de la base de datos de desarrollo `review_arena` → `duelo`
  (`docker-compose.yml` y valores por defecto de `config.py`).
- Nombre visible "Review Arena" → "Duelo": título de la API (y `docs/openapi.json`
  regenerado), interfaz, README, documentación, `openspec/config.yaml` y el `Purpose` del
  spec `frontend-shell`.
- Etiqueta de imagen del smoke test de CI y archivo `docs/spec/review-arena.md` →
  `docs/spec/duelo.md`.
- Carpeta local del proyecto `/var/home/renzo/Proyectos/new project` → `.../Duelo`
  (paso manual al final; se migra la memoria de Claude Code a la nueva ruta y se repara el
  worktree auxiliar).

No se tocan los changes archivados (`openspec/changes/archive/`): son historia y el nombre
antiguo es correcto en su momento.

## Capacidades

Ninguna (renombrado sin cambio de comportamiento, `skip_specs: true`).

## Impacto

Casi todo el backend (imports), configuración, docs y CI. Sin cambios de lógica. Efecto local:
la base de datos de desarrollo cambia de usuario y nombre, así que el volumen de Postgres
existente (con datos de prueba) no se reutiliza; el cambio de nombre de carpeta ya hace que
compose cree un volumen nuevo.
