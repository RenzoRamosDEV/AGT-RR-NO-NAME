# Proposal

## Why

La revisión de la PR de `temporal-readable-workflows` encontró un defecto real: `result_from_review()`
copiaba el resumen, los ficheros y los mensajes de los hallazgos de una review **completada** al
resultado de la activity, y con él al historial de Temporal, que es **inmutable**. Solo el `error` de una
review fallida pasaba por la redacción de credenciales. Un revisor que avisa de que hay un `token=…`, un
`Bearer …` o un `sk-…` en el diff lo cita en su resumen, y esa credencial quedaría persistida para
siempre en un lugar del que no se puede borrar. Lo mismo ocurría con el título del change (lo escribe
el autor del commit), que va en la entrada del workflow y en sus resúmenes estáticos.

Además, el mismo patrón heredado vivía en `frontend/src/lib/sanitize.ts` y tenía un fallo: en
`Authorization: Bearer abc` ocultaba solo la palabra «Bearer» y dejaba el token a la vista.

## What Changes

- Todo texto libre que entra en el historial de Temporal pasa por `redact_secrets()` **antes** de
  acotarse: resumen, fichero, mensaje y severidad de cada hallazgo, error, título del change (en la
  entrada del workflow, el resumen y la ficha estáticos) y los «Current Details» del hijo (defensa en
  profundidad).
- `redact_secrets()` cubre además de `token=…`, `Authorization: Bearer …` y `sk-…`: tokens de GitHub
  (`ghp_…`), claves de acceso de AWS, tokens de Slack, JWT y claves privadas PEM. El esquema de una
  cabecera `Authorization` se consume con su valor.
- `sanitizeError()` del frontend usa el mismo criterio (y corrige el fallo de `Authorization: Bearer`).
- Se documentan dos riesgos aceptados de `temporal-readable-workflows` (colisión de `sha12` y carrera del
  starter en un despliegue mixto), sin cambios de código.

## Capabilities

### Modified Capabilities
- `workflow-observability`: sin credenciales en el historial de Temporal.
- `frontend-shell`: el motivo de un fallo oculta también el valor tras un esquema de autorización y las
  credenciales con forma reconocible.

## Impact

- Código: `application/payload_limits.py`, `application/workflow_naming.py`, `workflows/dto.py`,
  `workflows/review_details.py`, `adapters/orchestration/temporal_review_starter.py` y
  `frontend/src/lib/sanitize.ts`.
- API y base de datos: sin cambios. La tabla `reviews` y la API de lectura siguen guardando y
  devolviendo el texto original; solo el historial de Temporal sale redactado.
- Docs: `design.md` (riesgos aceptados), README y `docs/architecture.md`.
