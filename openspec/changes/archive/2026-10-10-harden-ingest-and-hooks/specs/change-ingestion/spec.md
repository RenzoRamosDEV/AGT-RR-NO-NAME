## ADDED Requirements

### Requirement: Tamaño máximo del cuerpo de la ingesta
`POST /ingest/commit` y `POST /ingest/pr` SHALL rechazar con 413 una petición cuyo cuerpo supere
`MAX_INGEST_BODY_BYTES` (1 500 000 por defecto). Si la cabecera `Content-Length` ya supera el límite,
SHALL responder sin leer el cuerpo; si no hay `Content-Length`, SHALL contar los bytes recibidos y
cortar al superarlo. La respuesta SHALL ser un JSON con `detail` y SHALL NOT incluir ni registrar nada
del cuerpo. El límite SHALL aplicarse antes que la autenticación y el límite de peticiones. Este límite
protege la memoria y es independiente del truncado del diff (`MAX_DIFF_CHARS`): un cuerpo que cabe pero
con un diff mayor que ese máximo SHALL seguir dando 202 con `diff_truncated=true`. Las demás rutas no
SHALL verse afectadas.

#### Scenario: Cuerpo enorme con Content-Length
- **WHEN** llega un `POST /ingest/commit` con `Content-Length` mayor que el límite
- **THEN** la respuesta es 413 y el cuerpo no se lee

#### Scenario: Cuerpo enorme sin Content-Length
- **WHEN** llega un `POST /ingest/pr` por trozos cuya suma supera el límite
- **THEN** la respuesta es 413 sin procesar la petición

#### Scenario: Diff largo pero cuerpo permitido
- **WHEN** el cuerpo cabe en el límite y el diff supera `MAX_DIFF_CHARS`
- **THEN** la respuesta es 202 con `diff_truncated=true`

#### Scenario: Otras rutas
- **WHEN** se envía un cuerpo grande a otra ruta
- **THEN** este límite no interviene
