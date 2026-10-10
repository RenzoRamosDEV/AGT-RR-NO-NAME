## ADDED Requirements

### Requirement: Sin credenciales en el historial de Temporal
Todo texto libre que Duelo copie al historial de Temporal SHALL salir sin credenciales y SHALL
redactarse antes de acotarse a su longitud máxima. Alcanza al resumen, el fichero, el mensaje y la
severidad de cada hallazgo, al error de una review fallida, al título del change (en la entrada del
workflow y en los resúmenes y fichas estáticos) y a los «Current Details». Se ocultan los pares
`token`, `secret`, `password`, `passwd`, `api_key` y `authorization` con su valor (incluido el esquema
`Bearer` o `Basic`), `Bearer …`, `sk-…`, los tokens de GitHub, las claves de acceso de AWS, los tokens
de Slack, los JWT y las claves privadas PEM. La tabla `reviews` y la API de lectura NO cambian.

#### Scenario: Credencial citada en una review completada
- **WHEN** un agente completa su review con el resumen «El diff incluye token=abc123 y la clave sk-abcdefghijklmnop1234»
- **THEN** el resultado de la activity lleva «El diff incluye token=[oculto] y la clave [oculto]» y
  ningún evento del historial contiene `abc123` ni la clave

#### Scenario: Credencial en un hallazgo
- **WHEN** un hallazgo dice «password = hunter2 escrito en el código» sobre un fichero `sk-abcdefghijklmnop1234.env`
- **THEN** su mensaje y su fichero salen con el valor oculto

#### Scenario: Credencial en el título del commit
- **WHEN** el título del change es «fix: usar token=abc123»
- **THEN** la entrada del workflow, su resumen estático y su ficha llevan `token=[oculto]`

#### Scenario: Cabecera Authorization
- **WHEN** un texto contiene `Authorization: Bearer eyJhbGci.payload`
- **THEN** se oculta el token y no solo la palabra «Bearer»

#### Scenario: Se redacta antes de cortar
- **WHEN** una credencial queda partida por el límite de longitud
- **THEN** no queda ningún fragmento de ella a la vista

#### Scenario: Redactar no es truncar
- **WHEN** un texto solo cambia por la redacción
- **THEN** `truncated` sigue siendo `false`
