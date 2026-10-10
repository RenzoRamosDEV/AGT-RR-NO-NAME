# Tasks

## 1. Dominio y aplicación

- [x] 1.1 `domain/commit_state.py`: `CommitState`, `commit_state_of`, `parse_reverted_sha`, `is_safe_sha_argument` y la decisión pura de alcanzabilidad (conjunto, ventana, desmarcado) con tests unitarios y de propiedades
- [x] 1.2 `Change` con `discarded_at` y `reverts_sha`; eventos `commit.discarded`, `commit.restored` y `commit.reverted`; lista blanca de eventos
- [x] 1.3 Ingesta: campo `body`; el SHA revertido se guarda en el commit de revert (en cualquier orden de llegada)
- [x] 1.4 Barrido de alcanzabilidad (`application/reachability.py`) con puertos `RepositoryHistory` y `CommitMarks`
- [x] 1.5 Lectura: `commit_state` y `reverted_by` en el listado (LATERAL) y el detalle (`live_reverter`)

## 2. Adaptadores y composición

- [x] 2.1 `adapters/git/history.py` con `git log --all` y las comprobaciones individuales (SHA validado)
- [x] 2.2 Persistencia: migración (`discarded_at`, `reverts_sha`, índice parcial), modelos, repositorio de marcas, evento `commit.reverted` al crear el revert
- [x] 2.3 Configuración `REACHABILITY_SWEEP_INTERVAL_SECONDS` y `REACHABILITY_WINDOW_COMMITS`, tarea de fondo y cableado
- [x] 2.4 Hook: `body` en la carga; esquema y respuesta de la API; OpenAPI regenerado

## 3. Frontend

- [x] 3.1 Tipos, cliente y mock con un commit deshecho, otro revertido y el commit que lo revierte
- [x] 3.2 Fila ámbar con icono, etiqueta central y subtítulo (tarjetas, compacta y móvil)
- [x] 3.3 Aviso del detalle con enlace al revert y recuentos «N deshechos · N revertidos» en la cabecera de la lista

## 4. Verificación y cierre

- [x] 4.1 Tests de integración con repos git reales y Postgres real, migración arriba y abajo y e2e
- [x] 4.2 Capturas del frontend (oscuro, claro, compacta, detalle, móvil)
- [x] 4.3 `just ci`, mutación en los módulos nuevos, docs actualizadas
