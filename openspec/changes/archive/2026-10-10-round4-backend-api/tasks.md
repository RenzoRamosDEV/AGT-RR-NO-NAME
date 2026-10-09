# Tasks

## 1. Configuración

- [x] 1.1 `ALLOWED_ORIGINS`, `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` y `STALE_AFTER_SECONDS` en `Settings` con validación (sin `*`, orígenes con esquema y sin ruta, valores positivos); verificar en `test_config.py`

## 2. CORS

- [x] 2.1 Middleware CORS solo con orígenes configurados, sin credenciales; verificar con tests de API (origen permitido, no permitido, sin configuración, preflight)

## 3. Request ID y access log

- [x] 3.1 Middleware ASGI con `X-Request-ID` validado y log JSON en `duelo.access` (plantilla de ruta, sin query ni cabeceras); verificar con tests (id válido/inválido, token y query ausentes del log, 404)

## 4. Índices y consulta del canal

- [x] 4.1 Reescribir el contador de reviews como `LEFT JOIN LATERAL` en `list_for_project`; verificar con los tests de paridad existentes
- [x] 4.2 Migración reversible de índices (tras `c3f1a7d92b40`) y modelos al día; verificar con test de migración up/down, deriva modelos/esquema y un test que comprueba con EXPLAIN que el canal usa los índices

## 5. Rate limit

- [x] 5.1 Puerto `RateLimiter`, adaptador en memoria con reloj inyectable y purga de claves; verificar con tests unitarios (límite, ventana deslizante, claves independientes, acotado)
- [x] 5.2 Dependencia previa a la autenticación en `POST /ingest/*` y `/changes/{id}/retry`, 429 con `Retry-After` documentado en OpenAPI y composición con `RATE_LIMIT_REQUESTS=0` desactivado; verificar con tests de API

## 6. Reviews atascadas

- [x] 6.1 `is_stale` en dominio y `stale` en `ChangeSummary`/`ChangeDetail` con reloj y umbral inyectados; verificar con tests de dominio, de caso de uso y de API
- [x] 6.2 Campo `stale` en los schemas de listado y detalle

## 7. Documentación y cierre

- [x] 7.1 Regenerar `docs/openapi.json`; actualizar `docs/architecture.md`, `docs/testing.md`, `README.md` (variables nuevas, incl. `OPERATOR_TOKEN`) y `docker-compose.yml`
- [x] 7.2 `just lint`, `just test` y `just mutation` en verde; arreglar la intermitencia de schemathesis con `q` (NUL) declarando el patrón en el esquema
