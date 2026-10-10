# change-ingestion Specification

## Purpose
Permite al sistema recibir los datos de un cambio (commit o PR) de un proyecto y dejarlo
persistido junto con su evento de dominio de forma atómica y sin duplicados, para que
fases posteriores (workflows, API de ingesta) tengan una base fiable sobre la que disparar
reviews sin perder ni duplicar trabajo.

## Requirements

### Requirement: Persistencia atómica de un Change y su evento
El sistema SHALL persistir un `Change` nuevo y su evento `change.created` en una única
transacción: si cualquiera de las dos escrituras falla, ninguna de las dos debe quedar
persistida.

#### Scenario: Ingesta exitosa
- **WHEN** se ingesta un change válido para un proyecto existente
- **THEN** el `Change` queda persistido y existe exactamente un evento `change.created`
  asociado a él, visible en el mismo orden en que ocurrió

#### Scenario: Fallo durante la escritura del evento
- **WHEN** la escritura del `Change` se completa pero la escritura de su evento falla
- **THEN** la transacción se revierte por completo y el `Change` tampoco queda persistido

### Requirement: Identidad única por proyecto, tipo y referencia
El sistema SHALL tratar la combinación (proyecto, tipo de change, referencia de commit)
como la identidad natural de un `Change`: ingestar la misma combinación más de una vez
SHALL ser una operación idempotente, no SHALL crear una fila duplicada.

#### Scenario: Reingesta del mismo commit
- **WHEN** se ingesta dos veces un change con el mismo proyecto, tipo `commit` y el mismo
  `head_sha`
- **THEN** solo existe un `Change` para esa combinación y no se crea un segundo evento
  `change.created`

#### Scenario: Mismo commit, proyectos distintos
- **WHEN** dos proyectos distintos ingestan un change con el mismo `head_sha`
- **THEN** ambos quedan persistidos como `Change` independientes, cada uno con su propio
  evento

### Requirement: Recuperar un Change por su identificador
El sistema SHALL permitir recuperar un `Change` previamente persistido a partir de su
identificador, devolviendo nada si no existe.

#### Scenario: El change existe
- **WHEN** se solicita un `Change` por un id que fue persistido antes
- **THEN** se devuelve ese `Change` con todos sus campos

#### Scenario: El change no existe
- **WHEN** se solicita un `Change` por un id que nunca fue persistido
- **THEN** no se devuelve ningún `Change` (sin lanzar error)

### Requirement: Identificadores y enlaces acotados
El sistema SHALL rechazar, antes de persistir nada, un `Change` cuyo `head_sha` esté vacío,
supere 64 caracteres o contenga NUL, o cuyo `ref` supere 255 caracteres o su `url` supere
1000 (o contengan NUL), con un error de validación que indique el campo.

#### Scenario: head_sha en el límite
- **WHEN** se ingesta un change con `head_sha` de exactamente 64 caracteres
- **THEN** el change se persiste

#### Scenario: head_sha por encima del límite
- **WHEN** se ingesta un change con `head_sha` de 65 caracteres
- **THEN** se rechaza con un error de validación sobre `head_sha` y no se persiste nada

#### Scenario: head_sha vacío
- **WHEN** se ingesta un change con `head_sha` vacío
- **THEN** se rechaza con un error de validación sobre `head_sha`

#### Scenario: ref y url en el límite y por encima
- **WHEN** se ingesta un change con `ref` de 255 y `url` de 1000 caracteres
- **THEN** el change se persiste; con `ref` de 256 o `url` de 1001 se rechaza indicando
  el campo

### Requirement: Metadatos de visualización recortados
El sistema SHALL recortar el `title` a 500 caracteres y el `author` a 255 en vez de
rechazar el change, de modo que un asunto demasiado largo no impida su review.

#### Scenario: title por encima del límite
- **WHEN** se ingesta un change con un `title` de 501 caracteres
- **THEN** se persiste con un `title` de 500 caracteres que es el prefijo del original

#### Scenario: title y author en el límite
- **WHEN** se ingesta un change con `title` de 500 y `author` de 255 caracteres
- **THEN** se persisten íntegros

### Requirement: Contenido con carácter NUL
El sistema SHALL aceptar `title`, `author` y diff que contengan el carácter NUL (U+0000),
sustituyéndolo por U+FFFD al persistir, porque la base de datos no puede almacenarlo.

#### Scenario: Diff con NUL
- **WHEN** se ingesta un change cuyo diff contiene un NUL
- **THEN** el change se persiste y al recuperarlo el diff contiene U+FFFD en lugar del NUL

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

### Requirement: Cuerpo del mensaje opcional en la ingesta
`POST /ingest/commit` y `POST /ingest/pr` SHALL aceptar un campo opcional `body` (cuerpo del mensaje
del commit, de hasta 20 000 caracteres) que sirve para detectar los commits de revert. Su ausencia
SHALL ser equivalente a una cadena vacía, de modo que los hooks ya instalados sigan funcionando. El
hook de git SHALL enviarlo acotado a 4 000 caracteres.

#### Scenario: Hook antiguo
- **WHEN** llega una petición sin `body`
- **THEN** se procesa igual que antes y no se detecta ningún revert

#### Scenario: Cuerpo demasiado largo
- **WHEN** `body` supera 20 000 caracteres
- **THEN** la API responde 422
