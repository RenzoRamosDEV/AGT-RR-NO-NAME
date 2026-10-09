# review-raw-output Specification

## Purpose
Descarga de la salida cruda de una review solo para el operador.

## ADDED Requirements

### Requirement: Salida cruda de una review para el operador
El sistema SHALL exponer `GET /reviews/{id}/raw-output`, protegido con la cabecera
`X-Operator-Token`, que se compara en tiempo constante con `OPERATOR_TOKEN`. Este token SHALL ser
distinto de `INGEST_TOKEN` (la configuración rechaza que coincidan) y tener al menos 16
caracteres. Si `OPERATOR_TOKEN` no está configurado, el endpoint SHALL responder 404 a toda
petición, con o sin cabecera. Configurado: sin cabecera o con un token inválido, 401 (el token de
ingesta NO SHALL valer); con token válido, 200 con `review_id` y `raw_output`, y la cabecera
`Cache-Control: no-store`. Una review inexistente o sin salida cruda (las fallidas) SHALL
responder 404. El resto de respuestas de la API NO SHALL incluir `raw_output`.

#### Scenario: Token de operador válido
- **WHEN** hay `OPERATOR_TOKEN` configurado y se pide la salida cruda de una review completada
  con ese token
- **THEN** la respuesta es 200 con el `raw_output` guardado y `Cache-Control: no-store`

#### Scenario: Token inválido o ausente
- **WHEN** falta la cabecera o el token es incorrecto
- **THEN** la respuesta es 401 sin contenido de la review

#### Scenario: El token de ingesta no sirve
- **WHEN** se envía el `INGEST_TOKEN` como `X-Operator-Token`
- **THEN** la respuesta es 401

#### Scenario: Endpoint deshabilitado
- **WHEN** no hay `OPERATOR_TOKEN` configurado
- **THEN** la respuesta es 404 aunque se envíe cualquier token

#### Scenario: Review inexistente o sin salida cruda
- **WHEN** la review no existe o es una review fallida
- **THEN** la respuesta es 404

#### Scenario: Configuración insegura
- **WHEN** `OPERATOR_TOKEN` es igual a `INGEST_TOKEN` o tiene menos de 16 caracteres
- **THEN** la API no arranca (error de configuración)
