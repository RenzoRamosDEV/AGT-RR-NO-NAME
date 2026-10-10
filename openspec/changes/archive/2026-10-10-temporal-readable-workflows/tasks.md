# Tasks

## 1. Nombres legibles

- [x] 1.1 `application/workflow_naming.py` (saneado del repo, `sha12`, `proyecto6`, ids de padre e hijo, ids antiguos, `one_line`, `escape_markdown`, `static_summary`, `static_details`); verificar con tests unitarios exactos y el caso del proyecto quitado y vuelto a añadir
- [x] 1.2 Puerto `ProjectSlugs` + `SqlAlchemyProjectRepository.slug_of`; `TemporalReviewStarter` con id legible, resumen y ficha estáticos; padre e hijo con `workflow.patched`; verificar con tests de integración sobre Temporal de test (ids `commit-…`, `pr-…`, `review-…`, proyecto desconocido, fallo de la consulta de nombre)
- [x] 1.3 Guarda del id antiguo en el starter (en marcha / completado ⇒ no arranca; fallido ⇒ sí; `run` 2 con su id); verificar con tests de integración y comprobar que fallan sin la guarda

## 2. Respuesta del reviewer en Temporal

- [x] 2.1 `application/payload_limits.py` (acotado, control, credenciales) y `RunReviewResult` extendido con `result_from_review`; verificar con tests unitarios (límites exactos, sin `raw_output`, ida y vuelta por el conversor de Temporal, resultado antiguo que se deserializa)
- [x] 2.2 Resumen de cada actividad, «Current Details» del hijo (`workflows/review_details.py`) y resumen/ficha del padre y del hijo; verificar sobre el historial real con Temporal de test (resultado de cada actividad, resúmenes, detalles, fallo con credencial saneada)

## 3. Compatibilidad

- [x] 3.1 Replay de historias anteriores (padre con hijo `review-{change}-r{run}` y hijo sin compensación) y de una nueva; entrada antigua sin datos de presentación; despliegue gradual (campos extra ignorados en las dos direcciones)

## 4. Servidor y docs

- [x] 4.1 Verificar contra un Temporal real de prueba (otro pod): 1.24.2 descarta los metadatos, 1.26.2 los guarda, UI 2.31.2 no los pinta y 2.36.1 sí; actualizar 1.24.2 → 1.26.2 sobre la misma base de datos conserva los workflows; `docker-compose.yml` con `auto-setup:1.26.2` y `ui:2.36.1`
- [x] 4.2 `openspec/config.yaml`, `README.md`, `docs/architecture.md`, `docs/testing.md` y `docs/flujo-duelo.html` al día

## 5. Cierre

- [x] 5.1 `just ci` en verde y mutación sobre los módulos tocados
