# request-observability Specification

## Purpose
Poder seguir una petición en los logs sin exponer datos sensibles.

## Requirements

### Requirement: Identificador de petición
Toda respuesta de la API SHALL llevar la cabecera `X-Request-ID`. Si la petición trae un
`X-Request-ID` que cumple `^[A-Za-z0-9._-]{8,64}$`, SHALL devolverse el mismo; en otro caso (vacío,
demasiado corto o largo, con espacios o saltos de línea u otros caracteres) SHALL generarse uno
nuevo.

#### Scenario: Identificador válido entrante
- **WHEN** la petición trae `X-Request-ID: abc12345-trace`
- **THEN** la respuesta devuelve `X-Request-ID: abc12345-trace`

#### Scenario: Identificador inválido entrante
- **WHEN** el valor trae caracteres fuera del patrón o longitud incorrecta
- **THEN** la respuesta devuelve uno generado y el valor recibido no aparece en ningún log

### Requirement: Access log estructurado
El sistema SHALL emitir, por cada petición atendida, una línea JSON en el logger `duelo.access` con
`request_id`, `method`, `path` (la plantilla de la ruta, no la URL real), `status` y
`duration_ms`. NO SHALL registrar cuerpo, query string, ni cabeceras, de modo que ningún token pueda
aparecer en el log.

#### Scenario: Petición con token y query
- **WHEN** se llama a `GET /projects/acme/widgets/changes?q=secreto` con `X-Ingest-Token`
- **THEN** el log contiene la plantilla de la ruta, el estado y la latencia, y no contiene el valor
  de `q` ni el token

#### Scenario: Ruta inexistente
- **WHEN** se pide una ruta que no existe
- **THEN** el log registra el estado 404 con `path` igual a `<unmatched>`
