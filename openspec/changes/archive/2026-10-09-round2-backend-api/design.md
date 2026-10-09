# Design

## Context

Ver `proposal.md - Por qué`. El modelo ya tiene `changes.run` y `reviews(change_id, agent, run)`
único; el workflow `ReviewCommitWorkflow` ya recibe `run` y lo propaga a las activities y al id
del hijo (`review-{change_id}-r{run}`). Este change aprovecha eso: no modifica ningún workflow.

## Goals / Non-Goals

**Goals:**
- Estado de review agregado, único y testeado, usado igual por el listado, el detalle, el
  filtro y el reintento.
- Reintento seguro: sin dobles arranques y sin tocar el id de las ejecuciones en vuelo.
- Filtros que no cargan diffs ni rompen la paginación por cursor.

**Non-Goals:**
- Frontend, resumen de findings en el listado, detectar cancelaciones sin consultar a Temporal,
  autenticación de lecturas.

## Decisions

**`review_status` es una función pura sobre contadores, en `domain/review_status.py`.** Entradas:
reviews completadas y fallidas del `run` actual y número de agentes esperados (la
configuración `agent_names`). `total = completadas + fallidas`:
`total == 0` → `pending`; `total < esperados` → `running`; si no, sin fallos → `completed`,
sin completadas → `failed`, mezcla → `partial_failed`. Una review fallida de un agente mientras
el otro aún corre sigue siendo `running`: el resultado final no se conoce. Es una función de
contadores (y no de objetos `Review`) para que el listado pueda alimentarla desde una consulta
agregada sin cargar reviews.

**El filtro `status` se traduce a un predicado SQL sobre los mismos contadores.** El listado hace
`LEFT JOIN` con una subconsulta que cuenta, por change, las reviews cuyo `run` es el `run` actual
del change. Los contadores se devuelven en cada fila y el estado se deriva en Python con la
función de dominio (una única fuente para la salida); el filtro usa un predicado SQL con los
mismos umbrales, y un test de integración recorre la matriz de contadores para garantizar que
ambos coinciden. `status` es repetible (`?status=pending&status=running` es "en curso" para la
UI) y se combina con `kind` y `q`. El cursor sigue siendo posicional sobre `(created_at, id)`:
los filtros no lo invalidan, solo estrechan el conjunto.

**`q` se busca con `ILIKE` escapado, no con índices de texto.** `q` se recorta y, si queda vacío,
se ignora; coincide por subcadena en `title`, `author`, `head_sha` y `ref`. Los caracteres
`%`, `_` y `\` se escapan (`icontains(..., autoescape=True)`) para que una búsqueda `50%` no
sea un comodín. Un `q` con NUL es 422 (Postgres lo rechazaría con un 500) y más de 100
caracteres también. Sin `pg_trgm`: el volumen de un usuario local no lo justifica y el filtro
por proyecto ya acota el conjunto; se revisará si crece.

**Reintento: `run + 1`, id de workflow nuevo para `run > 1`, y `run` solo avanza con
compare-and-swap.** Los workflow ids siguen siendo `{kind}-{project}-{sha}` para `run == 1`
(las ejecuciones en vuelo no cambian) y pasan a `{kind}-{project}-{sha}-r{run}` para
`run > 1`; el id del padre era único por change y una ejecución fallida con
`ALLOW_DUPLICATE_FAILED_ONLY` no es reutilizable sin cambiar el run (las activities son
idempotentes por `(change, agent, run)`, así que repetir el mismo run no produciría reviews
nuevas). El caso de uso `retry_review`:

1. Carga el change (inexistente → 404) y sus reviews; si el estado del `run` actual no es
   `failed` ni `partial_failed` → `RetryNotAllowed` (409). Una review `completed` nunca se
   relanza: gastaría a los agentes otra vez.
2. Arranca el workflow del `run` siguiente. Es idempotente por id: dos peticiones simultáneas
   producen una sola ejecución (la segunda recibe `WorkflowAlreadyStarted`, que el starter ya
   trata como éxito).
3. Solo después avanza `changes.run` con `UPDATE ... SET run = run + 1 WHERE id = :id AND run = :run`
   (compare-and-swap). Si falla el arranque, `run` no avanza y se puede reintentar; si dos
   peticiones compiten, solo una cambia la fila y ambas devuelven el change con el `run`
   resultante.

Orden "arrancar y luego avanzar" (y no al revés): si avanzara primero y el arranque fallara, el
change quedaría en un `run` sin reviews (`pending`), que no es reintentable, y quedaría atascado.
Con este orden el peor caso es un workflow arrancado cuyo `run` aún no avanzó, y el siguiente
reintento lo reconcilia por el id determinista.

**Limitación conocida:** una ejecución cancelada o terminada sin llegar a persistir ninguna review
se ve como `pending`/`running` y no es reintentable por esta vía; distinguirla exige consultar a
Temporal (`describe`) y queda fuera. Reenviar el commit (`POST /ingest/commit`) sigue
reintentando el arranque como hasta ahora.

**El reintento exige `X-Ingest-Token`.** Es una escritura que consume cuota de los agentes; las
lecturas siguen abiertas (ver el `design.md` de `round1-backend-api`).

**Resumen de findings: normalización en lectura, sin migrar datos.** Las severidades guardadas son
cadenas libres (el contrato de los agentes dice `bug|risk|improvement|nit`, pero un agente puede
devolver otra cosa). `normalize_severity` recorta, pasa a minúsculas y mapea sinónimos
conocidos (`error`/`critical` → `bug`, `warning` → `risk`, `suggestion` → `improvement`,
`style`/`info` → `nit`); lo desconocido cuenta como `other`. Cuenta solo las reviews del `run`
actual (las de runs anteriores quedaron superadas) y nunca expone `raw_output`. Va en el detalle,
no en el listado: agregar JSONB por cada change del canal es caro y el listado ya expone
`review_status`.

**`GET /health/dependencies` es diagnóstico, no readiness.** Reutiliza las mismas comprobaciones
que `/ready` (`readiness_checks`) y devuelve 200 siempre, con `status` (`ok` o `degraded`) y, por
dependencia, `status`, `latency_ms` y, si falla, `reason` de vocabulario cerrado (`timeout` o
`error`): nunca el texto de la excepción (puede contener credenciales). Cada comprobación tiene
el mismo timeout que `/ready` y se ejecutan en paralelo. `/ready` sigue siendo el sondeo para
orquestadores (503 si falla).
