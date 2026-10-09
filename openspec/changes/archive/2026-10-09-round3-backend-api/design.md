# Design

## Context

Ver `proposal.md - Por qué`. Los diffs viven en `changes.diff` (acotados por `max_diff_chars`) y
los eventos del outbox en `events` (`type`, `payload` JSONB con `change_id`). El listado del
canal ya selecciona columnas concretas para no mover diffs.

## Goals / Non-Goals

**Goals:**
- Resumen del diff calculado en el dominio (una sola implementación, testeada) y persistido,
  de modo que el canal lo muestre sin cargar el diff.
- Distinguir ingesta nueva de duplicada sin cambiar el puerto `ChangeRepository.add`.
- Salida cruda solo para el operador, con un secreto distinto y sin ampliar la superficie pública.

**Non-Goals:**
- Frontend, rate limiting, paginación de eventos, autenticación de las lecturas públicas.

## Decisions

**`summarize_diff` es una función pura en `domain/diff.py`.** Recorre las líneas del diff:
`diff --git a/x b/y` abre un archivo (se usa la ruta de destino); `@@` entra en un hunk y las
líneas `+`/`-` dentro de un hunk cuentan como añadidas/borradas; `diff --git` sale del hunk, de
modo que las cabeceras `---`/`+++` no se cuentan y una línea de contenido que empiece por
`++`/`--` sí. Solo se entiende el formato de `git diff` (el que envían los hooks y GitHub). Un
diff truncado por `max_diff_chars` se resume tal cual llegó (el change ya marca `diff_truncated`).
`files_changed` es el recuento real; `files` se acota a 200 entradas para no inflar la fila ni la
respuesta del listado.

**Se guarda en una columna JSONB `changes.diff_summary`.** El resumen se calcula en
`Change.new` (dominio), no en el adaptador. Una sola columna JSONB en vez de cuatro porque nunca
se filtra ni agrega por ella. Los `Change` construidos sin resumen (tests) usan uno vacío.

**La migración rellena los changes existentes con una copia propia del algoritmo.** Una migración
debe ser un fotograma congelado: importar el dominio la rompería si el dominio cambia. Un test de
integración compara el relleno con `summarize_diff` sobre un corpus para detectar desvíos.
Se rellena por lotes con keyset sobre `id` para no cargar todos los diffs a la vez.

**`created` se deduce comparando ids, sin tocar `ChangeRepository.add`.** `Change.new` acepta un
`id` opcional; el caso de uso genera el id candidato y lo pasa. Si `add` devuelve un change con
otro id, ya existía (el contrato de `add` es precisamente devolver el existente). Así los
repositorios y sus fakes no cambian. El arranque de la review se ejecuta igualmente en la
reingesta (es idempotente y permite recuperar un fallo previo del starter).

**Stats por proyecto: `agent_stats(project_id | None)`.** Con proyecto se une `reviews` con
`changes` y se filtra por `changes.project_id`; el caso de uso resuelve el slug y lanza
`ProjectNotFound` (404) si no existe, para no confundir "proyecto sin reviews" (lista vacía) con
"proyecto mal escrito". Cuenta todos los runs, igual que el agregado global.

**Eventos: puerto `ChangeEventRepository` y lista blanca en la aplicación.** El adaptador lee
`events` filtrando por `project_id` y `payload->>'change_id'` (índice de expresión nuevo) y
ordena por `id`. La aplicación decide qué se expone: solo `change.created`, `review.completed` y
`review.failed`, y de cada payload solo `agent` y `review_id`. El `error` de `review.failed`
(texto de una excepción) y cualquier campo futuro se omiten por defecto: lo estable es la lista
blanca, no lo que haya en el JSONB.

**Salida cruda con `OPERATOR_TOKEN`, distinto de `INGEST_TOKEN`.** Riesgo: `raw_output` es la
salida íntegra de un agente sobre un diff privado; puede contener fragmentos de código, secretos
que el escáner no detectó o contenido inyectado. Por eso:
- Es opcional (`operator_token = None`) y sin él el endpoint responde 404 siempre, sin dar pistas
  de que existe. La configuración rechaza un token igual al de ingesta o de menos de 16
  caracteres: el token de ingesta lo llevan los hooks de los repos y no debe abrir lecturas.
- Se compara en tiempo constante (`hmac.compare_digest` sobre bytes), cabecera `X-Operator-Token`.
- 404 tanto si la review no existe como si no tiene salida cruda (las fallidas), para no ofrecer
  un oráculo de ids.
- La respuesta lleva `Cache-Control: no-store`; el endpoint no registra el contenido.
- No sustituye a la autenticación de lecturas: sigue pendiente antes de exponer la API fuera de
  `127.0.0.1` (ver `round1-backend-api`).

## Risks / Trade-offs

- Un diff con formato distinto de `git diff` produce un resumen vacío o parcial: aceptable, el
  resumen es informativo.
- La copia del algoritmo en la migración puede quedar desfasada: lo cubre el test de comparación.
- El índice sobre `payload->>'change_id'` añade coste de escritura en `events`: despreciable
  frente a escanear la tabla por cada consulta de eventos.
- `OPERATOR_TOKEN` no está en `docker-compose.yml` (fuera del alcance de backend): sin él el
  endpoint queda deshabilitado, que es el valor seguro por defecto.
