# Spec Delta

## ADDED Requirements

### Requirement: Entrada inválida sin efectos
El sistema SHALL responder 4xx, sin persistir nada ni arrancar ninguna review, cuando algún
campo de la petición contiene caracteres que la base de datos no admite (NUL) o supera sus
límites, en lugar de fallar con un error de servidor.

#### Scenario: NUL en el identificador del proyecto
- **WHEN** se envía un commit con token válido y un `project` que contiene `\x00`
- **THEN** la respuesta es 422, no se crea ningún `Change` y no se arranca ninguna review

### Requirement: Reingesta tras completar la review
El sistema SHALL NOT volver a arrancar la review de un commit cuya review ya se completó;
un commit cuya ejecución anterior falló o se canceló SHALL poder reintentarse reenviándolo.

#### Scenario: Reenvío de un commit con la review completada
- **WHEN** se reenvía un commit cuyo workflow de review ya terminó con éxito
- **THEN** no se crea una nueva ejecución de review para ese commit

#### Scenario: Reenvío de un commit cuya review falló
- **WHEN** se reenvía un commit cuyo workflow de review terminó en fallo
- **THEN** se arranca una nueva ejecución de review para ese commit
