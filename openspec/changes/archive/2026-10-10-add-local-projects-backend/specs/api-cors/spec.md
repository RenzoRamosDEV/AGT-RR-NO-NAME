## MODIFIED Requirements

### Requirement: Orígenes permitidos configurables
El sistema SHALL leer `ALLOWED_ORIGINS` (lista de orígenes `esquema://host[:puerto]` separados por
comas). Con la lista vacía (valor por defecto) la API NO SHALL enviar cabeceras CORS. Con orígenes
configurados SHALL responder a las peticiones de esos orígenes con `Access-Control-Allow-Origin`
igual al origen y a los preflight `OPTIONS` con 200, permitiendo los métodos `GET`, `POST` y
`DELETE` y las cabeceras `Content-Type`, `X-Ingest-Token` y `X-Request-ID`; SHALL exponer
`X-Request-ID` y `Retry-After`. NO SHALL permitir credenciales ni el origen `*`: un `*` en la lista,
o un origen sin esquema o con ruta, SHALL impedir el arranque con un error de configuración.

#### Scenario: Origen permitido
- **WHEN** `ALLOWED_ORIGINS=http://localhost:5173` y llega una petición con `Origin:
  http://localhost:5173`
- **THEN** la respuesta lleva `Access-Control-Allow-Origin: http://localhost:5173`

#### Scenario: Origen no permitido
- **WHEN** llega una petición con un origen que no está en la lista
- **THEN** la respuesta no lleva `Access-Control-Allow-Origin`

#### Scenario: Sin configuración
- **WHEN** `ALLOWED_ORIGINS` no está definida
- **THEN** ninguna respuesta lleva cabeceras CORS, ni siquiera un preflight

#### Scenario: Configuración insegura
- **WHEN** `ALLOWED_ORIGINS` contiene `*`, un origen sin esquema o con ruta
- **THEN** la configuración se rechaza al arrancar

#### Scenario: Preflight de un DELETE
- **WHEN** un origen permitido envía un preflight con `Access-Control-Request-Method: DELETE`
- **THEN** la respuesta es 200 y `Access-Control-Allow-Methods` incluye `DELETE`
