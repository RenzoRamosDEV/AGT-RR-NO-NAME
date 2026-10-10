# Tasks

## 1. Backend

- [x] 1.1 `redact_secrets` con más patrones (GitHub, AWS, Slack, JWT, PEM; esquema de `Authorization`) y `bound_redacted`; verificar con tests unitarios por patrón y el de «se redacta antes de cortar»
- [x] 1.2 `result_from_review` redacta resumen, fichero, mensaje y severidad; el título del change se sanea en la entrada del workflow y en el resumen y la ficha estáticos; los «Current Details» redactan otra vez; verificar con tests unitarios que fallaban antes del arreglo y con una prueba de integración que revisa los bytes de TODOS los eventos del historial (entrada, resultados, metadatos y detalles) con un agente que cita credenciales y un título con una credencial

## 2. Frontend

- [x] 2.1 `sanitizeError` con el mismo criterio (esquema de `Authorization`, credenciales con forma reconocible); verificar con tests de regresión que fallan con el saneado anterior; `pnpm lint`, `tsc -b`, `pnpm build` y `pnpm test` en verde

## 3. Docs y riesgos aceptados

- [x] 3.1 `design.md` con los dos riesgos aceptados de `temporal-readable-workflows` (colisión de `sha12`, carrera del starter en un despliegue mixto) y los límites de la redacción; README y `docs/architecture.md`

## 4. Cierre

- [x] 4.1 `just ci` en verde y mutación sobre los módulos tocados
