# Spec Delta

## ADDED Requirements

### Requirement: Recuperar un Change por su identificador
El sistema SHALL permitir recuperar un `Change` previamente persistido a partir de su
identificador, devolviendo nada si no existe.

#### Scenario: El change existe
- **WHEN** se solicita un `Change` por un id que fue persistido antes
- **THEN** se devuelve ese `Change` con todos sus campos

#### Scenario: El change no existe
- **WHEN** se solicita un `Change` por un id que nunca fue persistido
- **THEN** no se devuelve ningún `Change` (sin lanzar error)
