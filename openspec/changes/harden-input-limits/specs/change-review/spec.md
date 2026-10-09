# Spec Delta

## ADDED Requirements

### Requirement: Nombre de agente acotado
El sistema SHALL rechazar el registro de una `Review` cuyo nombre de agente esté vacío o
supere 50 caracteres, con un error de validación, antes de persistir nada.

#### Scenario: Nombre de agente en el límite
- **WHEN** se registra una review con un nombre de agente de exactamente 50 caracteres
- **THEN** la review se persiste

#### Scenario: Nombre de agente vacío o demasiado largo
- **WHEN** se registra una review con un nombre de agente vacío o de 51 caracteres
- **THEN** se rechaza con un error de validación y no se persiste nada

### Requirement: Contenido de review con carácter NUL
El sistema SHALL persistir una `Review` y su evento (`review.completed` o `review.failed`)
aunque su `summary`, `raw_output`, `error` o los textos de sus `findings` contengan el
carácter NUL, sustituyéndolo por U+FFFD, porque la base de datos no puede almacenarlo.

#### Scenario: Salida del agente con NUL
- **WHEN** un agente devuelve un resumen y un hallazgo cuyo texto contiene un NUL
- **THEN** la review se persiste y al leerla el texto contiene U+FFFD en lugar del NUL
