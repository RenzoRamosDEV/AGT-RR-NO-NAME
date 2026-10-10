# Tasks

## 1. Hook sin redirecciones

- [x] 1.1 `post()` con un opener que no sigue redirecciones y trata 3xx como fallo silencioso; verificar con un servidor local que responde 302 hacia otro servidor y comprueba que este nunca recibe petición ni token

## 2. Límite del cuerpo de la ingesta

- [x] 2.1 `MAX_INGEST_BODY_BYTES` en la configuración (por defecto 1 500 000, mayor que 0); verificar con test de configuración
- [x] 2.2 `BodyLimitMiddleware` (413 por `Content-Length` sin leer y por conteo del flujo) montado solo para `POST /ingest/commit` y `/ingest/pr`, dentro del contexto de petición; verificar con tests de middleware (límite exacto, un byte más, sin `Content-Length`, otras rutas intactas, el cuerpo no aparece en la respuesta ni en el log) y con un uvicorn real al que se suben 6 MB
- [x] 2.3 Un cuerpo bajo el límite con un diff mayor que `MAX_DIFF_CHARS` sigue dando 202 con `diff_truncated`; verificar con test de API
- [x] 2.4 El 413 consta en OpenAPI de las dos rutas y el contrato pasa; regenerar `docs/openapi.json`

## 3. Eventos cronológicos

- [x] 3.1 `list_for_change` ordena por `(created_at, id)` y el comentario del puerto lo dice; verificar con test de integración con eventos cuyo `id` y `created_at` van cruzados

## 4. Cierre

- [x] 4.1 `just ci` en verde (904 tests) y el gate de mutación en 746/750; el middleware, fuera del gate (`entrypoints`), se comprobó a mano con tres mutantes (frontera de `Content-Length`, frontera del conteo del flujo, filtro de rutas invertido) y los tres mueren; documentación al día
