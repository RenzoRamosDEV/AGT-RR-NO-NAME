## ADDED Requirements

### Requirement: El motivo de un fallo oculta las credenciales con el mismo criterio que el backend
El motivo sanitizado de una review fallida SHALL ocultar el valor que sigue al esquema de una cabecera
`Authorization` (`Bearer` o `Basic`), no solo la palabra del esquema, y las credenciales con forma
reconocible (tokens de GitHub, claves de AWS, tokens de Slack, JWT y claves privadas PEM).

#### Scenario: Cabecera Authorization
- **WHEN** una review fallida trae el error «cabecera Authorization: Bearer eyJhbGci.payload fin»
- **THEN** la card muestra «cabecera Authorization: [oculto] fin» y no el token

#### Scenario: Token de GitHub
- **WHEN** el error contiene un token `ghp_…`
- **THEN** la card lo muestra como `[oculto]`
