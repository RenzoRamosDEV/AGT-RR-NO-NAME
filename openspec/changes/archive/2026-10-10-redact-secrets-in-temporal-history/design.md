# Design

## Redacción antes de acotar

`bound_redacted(text, limit)` = `bound(redact_secrets(text), limit)`. El orden importa: si se cortara
primero, un `sk-…` partido por el límite dejaría de casar con el patrón y su principio quedaría a la
vista. Redactar no cuenta como truncado (`truncated` solo avisa de recortes por tamaño).

Qué pasa por ahí, y por qué es todo lo que puede llevar texto libre al historial:

| Texto | Dónde acaba en Temporal |
|---|---|
| `summary`, `file`, `message`, `severity` de los hallazgos | resultado de `run_review` (evento `ActivityTaskCompleted`) y resultado del hijo y del padre |
| `error` | igual (ya se redactaba) |
| título del change | **entrada** del padre (`ReviewCommitInput.title`), `static_summary` y `static_details` de padre e hijo |
| texto de las respuestas | «Current Details» del hijo: se redacta otra vez al pintar (defensa en profundidad) |

El nombre del agente (de `AGENT_NAMES`), el SHA, el nombre del repo y el `run` no son texto libre de un
tercero.

## Patrones

Además de los que ya había (`token|secret|password|passwd|api_key|authorization` seguidos de `=`/`:`,
`Bearer …`, `sk-…`): tokens de GitHub (`gh[pousr]_…`), ids de clave de AWS (`AKIA…`/`ASIA…`), tokens de
Slack (`xox[abprs]-…`), JWT (`eyJ….….…`) y bloques de clave privada PEM. El valor de un par
`authorization: Bearer abc` incluye el esquema (`Bearer`/`Basic`): antes se ocultaba solo «Bearer».

**Es heurístico, no una garantía.** Una contraseña sin palabra clave ni forma reconocible (por ejemplo
«la contraseña es hunter2» en prosa) no se detecta. Tiene falsos positivos asumidos: «token: valida»
oculta «valida». Se prefiere ocultar de más a persistir una credencial en un historial inmutable.

## Frontend

`sanitizeError()` es el mismo criterio en TypeScript (mismos patrones y orden). Corrige el fallo de
`Authorization: Bearer abc`. Queda fuera de este change: la API de lectura devuelve el resumen y los
hallazgos tal y como están en Postgres y la interfaz los pinta sin redactar (solo el motivo de un
fallo pasa por `sanitizeError`). Redactarlos en la lectura es otra decisión de producto.

## Límites conocidos

- **Mensajes de excepciones de infraestructura.** Cuando una activity falla de verdad (p. ej. Postgres
  caído), Temporal guarda el mensaje de la excepción en `ActivityTaskFailed`. Eso es del SDK, no de
  `result_from_review`, y no se toca aquí. La review fallida que se guarda en Duelo sí lleva un mensaje
  fijo (`INFRASTRUCTURE_FAILURE_MESSAGE`).
- **Historia ya escrita.** Los workflows que ya se ejecutaron con la versión anterior conservan lo que
  guardaron. Esto solo evita nuevas escrituras; el historial de Temporal no se puede reescribir.

## Riesgos aceptados de `temporal-readable-workflows` (sin código)

**Colisión del fragmento de SHA.** El id de padre e hijo lleva los 12 primeros hex del SHA (48 bits).
Dentro de **un mismo proyecto** (el sufijo `proyecto6` separa los proyectos), dos commits distintos con
los mismos 12 primeros hex producirían el mismo id. Con *n* commits en un proyecto la probabilidad es
del orden de *n*²/2 · 2⁻⁴⁸: con 10 000 commits, ~2·10⁻⁷. Se acepta: alargar el SHA o añadir un hash
ensuciaría los nombres, que son justo lo que se quería legible. **Efecto si ocurriera:** el segundo
arranque se ignora como «ya arrancado» y ese change se queda `pending` (`stale` lo marca tras
`STALE_AFTER_SECONDS`); la salida es reenviar el commit tras terminar el primero o reintentarlo.

**Carrera del starter en un despliegue mixto.** La guarda del id antiguo es «consulta y luego
arranca», no una operación atómica (Temporal no ofrece una barrera sobre dos ids). Solo falla si, a
la vez, **un API antiguo** (que arranca con el id viejo y no consulta nada) y **uno nuevo** reciben el
mismo commit: el nuevo puede consultar justo antes de que el antiguo arranque y arrancar también el suyo.
Resultado: los agentes se ejecutan dos veces para ese commit (las reviews no se duplican, porque
`UNIQUE (change, agent, run)` las absorbe, pero el CLI gasta suscripción dos veces). Hoy hay **un único
API y un único worker**, así que no ocurre. **Recomendación al desplegar:** drenar los productores
antiguos (parar el API antiguo y dejar terminar las ingestas en vuelo) antes de arrancar el nuevo, y
arrancar el worker nuevo a la vez que el API.
