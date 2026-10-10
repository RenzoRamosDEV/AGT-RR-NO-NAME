# Spec Delta

## ADDED Requirements

### Requirement: Política de reintentos de las activities de review
Las activities de una review (`run_review` y su compensación) SHALL reintentarse como máximo 3
veces en total, con espera inicial de 1 s, backoff exponencial de coeficiente 2 y una espera máxima
entre intentos de 1 min. La política SHALL definirse en un único sitio compartido con los plazos,
de modo que el workflow y la configuración no diverjan.

#### Scenario: Fallo transitorio
- **WHEN** la activity falla dos veces por un error transitorio y la tercera tiene éxito
- **THEN** la review queda persistida una sola vez y no hay un cuarto intento

#### Scenario: Esperas acotadas
- **WHEN** se consulta la política con la que el workflow ejecuta `run_review`
- **THEN** sus valores son 3 intentos, 1 s inicial, coeficiente 2 y 1 min de espera máxima
