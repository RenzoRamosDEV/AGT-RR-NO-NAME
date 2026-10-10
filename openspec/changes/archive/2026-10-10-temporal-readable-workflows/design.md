# Design

## Nombres

Funciones puras en `application/workflow_naming.py` (solo `str`/`int`), porque las usan el starter
(adaptador) y el workflow, que no puede leer la base de datos. El nombre del repo, el tipo, el SHA, el
UUID del proyecto y el título llegan al padre en `ReviewCommitInput` (campos nuevos con valor por
defecto); el starter obtiene el nombre con el puerto `ProjectSlugs` (`slug_of`), implementado por
`SqlAlchemyProjectRepository`. Un proyecto sin nombre conocido usa `proyecto`.

**Unicidad.** `{kind}-{repo}-{sha12}-{proyecto6}`. El nombre solo no basta: la política
`ALLOW_DUPLICATE_FAILED_ONLY` hace que un id ocupado por una ejecución completada ignore el arranque
sin avisar, y el nombre de un proyecto no es estable (se puede quitar y volver a añadir, o dos nombres
pueden coincidir una vez saneados: `Acme/Widgets` y `acme/widgets`). El UUID del proyecto sí lo es,
así que sus 6 primeros hex (16,7 millones de valores) completan el id. Lo único que podría colisionar
es que dos commits **del mismo proyecto** compartan los 12 primeros hex del SHA (2^-48 por pareja); se
acepta y queda documentado.

**El tipo también va en el id del hijo.** Una primera versión del id del hijo era
`review-{repo}-{sha12}-{proyecto6}-r{run}`, sin el tipo. Como un commit y una PR del mismo proyecto
con el mismo SHA son dos changes distintos, sus hijos compartían id: el segundo no arrancaba y la
review de la PR no se hacía nunca. Lo destapó el e2e de lectura (`test_read_flow.py`), que ingiere un
commit y una PR con el mismo SHA; antes no pasaba porque el id llevaba el `change_id`. Ahora es
`review-{kind}-{repo}-{sha12}-{proyecto6}-r{run}`, con tests unitario y de integración de regresión. No se usan search attributes personalizados: exigen registrarlos en el
servidor y, si faltan, el arranque falla; los ids legibles ya permiten filtrar por prefijo
(`WorkflowId STARTS_WITH "commit-acme-widgets"`) sin registrar nada.

## Respuesta del reviewer

`RunReviewResult` (resultado de la activity, y por tanto del hijo y del padre) pasa de
`{status, review_id}` a un extracto **acotado** de la `Review` ya persistida (`result_from_review`):
agente, resumen (2000), nota, hasta 30 hallazgos (mensaje y fichero de 300), `findings_total`, error
(sin credenciales, 300), duración y `truncated`. Se construye a partir de la fila que devuelve el
repositorio (en una reentrega, la existente), nunca del `raw_output`. Rompe a propósito la regla de
«por Temporal solo viajan IDs» (se actualiza `openspec/config.yaml`): el límite que importa es el de no
llevar datos pesados (diff, salida cruda), no el de no llevar el resultado.

**Saneado del error.** El error de una review fallida puede arrastrar lo que diga una excepción. En
Postgres ya se guardaba tal cual; en Temporal se copia con `redact_secrets` (`token=…`, `password=…`,
`Authorization: Bearer …`, `sk-…`) y acotado. Una prueba descubrió que el patrón heredado del frontend
dejaba el token a la vista en `Authorization: Bearer abc` (ocultaba solo «Bearer»); aquí el esquema se
consume con el valor. El frontend tiene el mismo defecto y queda fuera de este change.

**Compatibilidad de DTO.** Campos nuevos con valor por defecto. Comprobado con el conversor real de
Temporal en las dos direcciones: un histórico antiguo se deserializa y un worker antiguo ignora los
campos de más (despliegue gradual API/worker sin romper nada).

## Resúmenes y detalles

- `static_summary`/`static_details` del padre (al arrancar, en el starter) y del hijo
  (`execute_child_workflow`); `summary=` en cada `execute_activity`; `workflow.set_current_details` en
  el hijo, que se reescribe cada vez que termina un agente (`workflows/review_details.py`, función
  pura de los resultados que ya tiene el workflow, así que es determinista).
- Todo texto de un agente o un autor pasa por `escape_markdown` (escapa los caracteres especiales y
  `&`, `<`) y por `one_line`/acotado. Lo que va dentro de un bloque de código no se escapa (solo se
  quitan las comillas invertidas).

## Compatibilidad con ejecuciones en vuelo

El id del hijo se calcula **dentro** del workflow. Dos protecciones:

1. **La entrada.** Una ejecución arrancada antes del cambio no trae repo/SHA/proyecto: el padre usa el
   id antiguo del hijo. Es lo que de verdad protege las historias antiguas.
2. **`workflow.patched("readable-workflow-names")`**, en padre e hijo, que deja un marcador en las
   historias nuevas. **Medido:** el replay de una historia anterior pasa también sin el `patched`
   (se probó a quitarlo), porque (1) ya basta y los metadatos de usuario (`summary=`,
   `set_current_details`) no se comparan al reproducir en el SDK 1.34. Se mantiene como cinturón y
   tirantes por si una versión futura del SDK los compara.

## No relanzar agentes

Cambiar el id haría que reenviar un commit revisado antes del cambio lanzara a los agentes otra vez
(gasto de suscripción). El starter consulta antes el id antiguo con `describe()`: `NOT_FOUND` →
sigue; en marcha o completado → no arranca; fallido/cancelado/terminado/plazo → arranca con el id
nuevo (la misma regla de `ALLOW_DUPLICATE_FAILED_ONLY`). Se consulta con el `run` correspondiente.
Un fallo de la consulta que no sea `NOT_FOUND` se propaga como `ReviewStartError` (503, reintentable).
Límite: si Temporal ya borró la ejecución antigua por retención, se vuelve a revisar, como antes.

## Versiones de Temporal (medido, no supuesto)

Con un servidor de prueba propio (pod aparte, otros puertos) y los workflows reales de Duelo:

| Servidor | UI | Resultado |
|---|---|---|
| `auto-setup:1.24.2` (el del compose anterior) | — | **Descarta** los metadatos de usuario: `static_summary` y `static_details` vuelven vacíos, el resumen de la actividad no aparece y el evento de inicio no los trae. |
| `auto-setup:1.26.2` | — | Los guarda: `static_summary`, `static_details`, resumen de la actividad y `current_details` (consulta `__temporal_workflow_metadata`) correctos. |
| 1.26.2 | `ui:2.31.2` | Se ven los nombres, el **Result** del workflow y el resultado de cada actividad en el historial, pero **no** «Summary & Details» ni «Current Details». |
| 1.26.2 | `ui:2.36.1` | Además aparecen «Summary & Details», «Current Details» y la línea de tiempo etiqueta cada actividad («run_review • codex revisa 3f2a9c1»). |

No se probaron versiones intermedias: el compose pasa a `1.26.2` y `2.36.1`, las validadas.

**Actualizar sobre datos existentes.** Se creó una base de datos con 1.24.2 y varios workflows y se
sustituyó el servidor por 1.26.2 sobre el mismo Postgres: `auto-setup` aplicó solo las
actualizaciones de esquema (v1.13 y v1.14) y los 6 workflows siguieron listados con su historial
completo. Temporal recomienda subir una versión menor cada vez; aquí se saltó la 1.25 y funcionó, pero
la garantía es empírica, no de documentación. Quien tenga el stack levantado debe recrearlo (`just down
&& just dev`); el volumen se conserva.

## Riesgos

- El texto de las reviews, que puede citar código, queda en el historial de Temporal (Postgres local),
  además de en la tabla `reviews`. Es lo que se pide; se documenta.
- Los payloads de resultado crecen (~ KB por agente, acotados; muy por debajo de los 2 MB).
- Una nueva versión del servidor o de la UI de Temporal podría cambiar cómo se pintan los metadatos.
