# Design

## Decisiones

### CORS
`ALLOWED_ORIGINS` es una lista separada por comas (mismo patrón que `AGENT_NAMES`). Cada origen
debe ser `esquema://host[:puerto]` sin ruta; `*` se rechaza al arrancar. Vacía = no se instala el
middleware (la API no responde cabeceras CORS). `allow_credentials=False`: la autenticación va en
cabeceras `X-Ingest-Token`, no en cookies. Métodos `GET`, `POST`; cabeceras permitidas
`Content-Type`, `X-Ingest-Token`, `X-Request-ID`; se exponen `X-Request-ID` y `Retry-After`.
`X-Operator-Token` NO se permite desde navegador: la salida cruda es para el operador con `curl`.

### Request ID y access log
Middleware ASGI puro (no `BaseHTTPMiddleware`, que rompe el contexto y copia el cuerpo). El
identificador entrante solo se acepta si cumple `^[A-Za-z0-9._-]{8,64}$`; si no, se genera un
`uuid4().hex`. Así un cliente no puede inyectar saltos de línea ni texto arbitrario en los logs. El
log es una línea JSON en el logger `duelo.access` con `request_id`, `method`, `path` (la plantilla
de la ruta, p. ej. `/changes/{change_id}`, nunca la URL real con ids o query), `status` y
`duration_ms`. Sin ruta resuelta (404 del router) se registra `path: "<unmatched>"`. No se
registran cabeceras ni cuerpos, así que los tokens no pueden filtrarse.

### Índices y consulta del canal (medido con EXPLAIN)
Con 60 000 changes y 120 000 reviews en 5 proyectos, la consulta existente tardaba ~58 ms: agregaba
las reviews de TODO el proyecto en una subconsulta (con `Seq Scan` sobre `reviews`), la unía y
después ordenaba; los índices solos no cambiaban el plan. Se reescribe el contador como
`LEFT JOIN LATERAL` por change (cuenta las reviews del `run` actual) y con los índices el plan
pasa a `Index Scan Backward` sobre `changes` + `Index Only Scan` sobre `reviews` por cada change de
la página: ~0,6 ms sin filtro, ~0,4 ms con `kind`, ~4 ms con `status=failed` (se recorre el
índice hasta reunir 21 coincidencias).

Cambios de índices (la migración es reversible):
- `ix_changes_project_created_at (project_id, created_at)` → `(project_id, created_at, id)`: el
  orden del canal es `(created_at, id)` y así el índice cubre también el desempate y el cursor.
- Nuevo `(project_id, kind, created_at, id)` para el filtro por tipo.
- `ix_reviews_change_id (change_id)` → `(change_id, run, status)`: cubre el contador (index-only).
  El prefijo `change_id` sigue sirviendo a `list_for_change`.

La semántica no cambia: el predicado SQL de `review_status` y la función de dominio siguen siendo
equivalentes y los tests de paridad existentes los comparan.

### Rate limit
Puerto `RateLimiter` en `application/ports.py` (`async hit(key) -> RateLimitDecision`); adaptador
en memoria con ventana deslizante (cola de instantes por clave) y reloj inyectable. Se aplica como
dependencia de FastAPI ANTES de la autenticación, por IP del cliente y por grupo de ruta (`ingest`
y `retry`), así los intentos con token inválido también consumen cuota (frena fuerza bruta). La
composición instala el adaptador solo si `RATE_LIMIT_REQUESTS > 0`; con `0` no hay limitador y la
dependencia no hace nada. Por defecto 300 peticiones por 60 s: holgado para hooks de repos, y
`just load` (200 peticiones) pasa.

Limitaciones asumidas y documentadas:
- Es memoria de un proceso: con varios workers de uvicorn el límite efectivo es N veces mayor; para
  multi-proceso hará falta un adaptador compartido (Redis) tras el mismo puerto.
- Detrás de un proxy la IP es la del proxy salvo que uvicorn corra con `--proxy-headers`; no se
  lee `X-Forwarded-For` por cuenta propia (es falsificable).
- El estado se pierde al reiniciar y la memoria se acota: al superar 10 000 claves se purgan las
  vacías.

### Reviews atascadas
Función pura de dominio `is_stale(review_status, created_at, now, stale_after)`: verdadero si el
estado agregado es `pending` o `running` y `now - created_at > stale_after`. El caso de uso
recibe el reloj (`now`) y el umbral, así que los tests no dependen de la hora real. Se expone como
`stale: bool` en el listado y el detalle; no hay filtro nuevo ni acción automática.

Limitación: no se guarda cuándo empezó el `run` actual, solo `created_at` del change. Un reintento
sobre un change más antiguo que el umbral se mostraría `stale` hasta que registre una review. Es
solo diagnóstico, y evita una columna y una migración de datos; si molesta, el siguiente paso
natural es una columna `run_started_at`.

## Alternativas descartadas
- CORS con `*`: abre la API a cualquier origen; se exige lista explícita.
- Rate limit por token: el token es único y compartido, sería un límite global; y no frena la
  fuerza bruta sobre el propio token.
- Rate limit en Postgres: añade escrituras a cada petición; innecesario para un proceso.
- Autogenerar el access log con `uvicorn.access`: incluye la URL con query y no la plantilla.
