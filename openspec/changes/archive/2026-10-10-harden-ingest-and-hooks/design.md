# Design

## Decisiones

### F. Hook sin redirecciones
`post()` construye un opener con un `HTTPRedirectHandler` cuyo `redirect_request` devuelve `None`:
`urllib` lanza entonces `HTTPError` con el código 3xx en lugar de seguir. Ya hay un `except` genérico
alrededor del envío (los fallos del hook son silenciosos por diseño), así que un 3xx cuenta como
cualquier otro fallo. No se añade lista de hosts permitidos: la URL sale de `hook.env`, que escribe la
API, y no seguir redirecciones basta para que el token no salga de ese host.

### G. Límite del cuerpo
- Es un middleware ASGI puro (`BodyLimitMiddleware`) que solo actúa sobre `POST` a
  `/ingest/commit` y `/ingest/pr`; el resto pasa intacto.
- Con `Content-Length` mayor que el límite responde 413 **sin leer el cuerpo**.
- Sin `Content-Length` (transferencia por trozos) envuelve `receive`: acumula la cuenta de bytes y,
  si supera el límite, lanza una excepción interna que el propio middleware convierte en 413. Los
  trozos ya entregados no se almacenan en el middleware (solo se cuenta).
- Con `Content-Length` no numérico o negativo deja pasar la petición: el servidor ASGI ya rechaza
  una cabecera mal formada, y el conteo del flujo sigue protegiendo.
- Orden de middlewares: `RequestContextMiddleware` (más externo: el 413 lleva `X-Request-ID` y entra
  en el access log) → CORS → `BodyLimitMiddleware` → rutas. El 413 se emite **antes** del limitador de
  peticiones y del token (que son dependencias de la ruta): una petición enorme sin token no llega a
  leerse y no puede usarse para agotar memoria. Contrapartida: un cliente sin token ve 413 en lugar de
  401, lo que no revela nada (el tamaño máximo es público en la documentación).
- La respuesta es `{"detail": "El cuerpo supera el máximo de N bytes."}` con el límite configurado;
  no incluye nada del cuerpo ni se registra. El access log ya no recoge cuerpos.
- El límite HTTP es distinto del de negocio: `MAX_DIFF_CHARS` (200 000) sigue truncando el diff y
  marcando `diff_truncated`; el HTTP solo protege la memoria. Por defecto 1 500 000 bytes deja
  holgura para un diff de 200 000 caracteres con escapes JSON y multibyte, y para los 1 000 000 que
  ya trunca el hook.
- El 413 se declara en el OpenAPI de las dos rutas con `responses`.

### H. Orden de eventos
`ORDER BY created_at, id`: el instante manda y el `id` desempata de forma estable. No hay migración;
el índice de expresión sobre `payload->>'change_id'` sigue sirviendo el filtro y el conjunto por change
es pequeño.

## Riesgos
- Un cliente que mande un diff gigante recibirá 413 en lugar de 202 truncado. Es el comportamiento
  deseado y está documentado.
- Un proxy que reescriba `Content-Length` no cambia nada: el conteo del flujo cubre ese caso.
