# Spec Delta

## ADDED Requirements

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
