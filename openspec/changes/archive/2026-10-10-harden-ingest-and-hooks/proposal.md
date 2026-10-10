# Proposal

## Why

Tres defectos reales señalados por la revisión de Codex y por el informe del flujo:

1. **El token del hook puede viajar a otro host.** El hook envía con `urllib.request.urlopen`, que
   sigue redirecciones (un 302 se repite como `GET` conservando las cabeceras, entre ellas
   `X-Ingest-Token`). Si el servidor de la URL configurada redirige a otro host, el token y la
   petición salen de la API de Duelo.
2. **No hay límite de tamaño del cuerpo en la ingesta.** `diff` no tiene `max_length` en el esquema
   y el límite de 200 000 caracteres se aplica *después* de que FastAPI y Pydantic hayan leído y
   decodificado todo el JSON: un cuerpo enorme se carga entero en memoria antes de truncarse.
3. **La línea de tiempo de un change no es cronológica.** `GET /changes/{id}/events` ordena por el
   `id` autoincremental del outbox, no por `created_at`; con reviews concurrentes los eventos salen
   con los instantes cruzados.

## What Changes

- El hook usa un opener sin redirecciones: una respuesta 3xx se trata como fallo silencioso y el
  token nunca se envía a un segundo host.
- `POST /ingest/commit` y `POST /ingest/pr` rechazan con 413 un cuerpo mayor que
  `MAX_INGEST_BODY_BYTES` (1 500 000 por defecto), antes de leerlo si `Content-Length` ya lo supera
  y cortando el flujo si no hay `Content-Length`. El truncado del diff a `MAX_DIFF_CHARS` sigue
  siendo el límite de negocio y se aplica a los cuerpos que caben.
- `GET /changes/{id}/events` ordena por `(created_at, id)`.

## Capabilities

### Modified Capabilities
- `change-ingestion`: nuevo requisito «Tamaño máximo del cuerpo de la ingesta».
- `local-projects`: nuevo requisito «El hook no sigue redirecciones».
- `change-events`: nuevo requisito «Orden cronológico estable».

## Impact

- Código: `entrypoints/hook.py`, un middleware nuevo `entrypoints/api/body_limit.py`, `app.py`,
  `config.py`, `composition.py`, `adapters/persistence/event_repository.py` y el comentario del puerto.
- API: `POST /ingest/commit` y `POST /ingest/pr` documentan un 413 (cambio aditivo de contrato).
- Configuración: variable nueva `MAX_INGEST_BODY_BYTES` (opcional).
- Clientes con diffs de más de ~1,5 MB en JSON recibirán 413 en lugar de un 202 truncado; los hooks
  ya limitan el diff a 1 000 000 caracteres, así que no se ven afectados salvo con caracteres
  multibyte muy densos.
