## ADDED Requirements

### Requirement: El hook no sigue redirecciones
Al enviar a la API, el hook NUNCA SHALL seguir una redirección HTTP: una respuesta 3xx SHALL tratarse
como un fallo del envío (silencioso, como cualquier otro) y el token `X-Ingest-Token` SHALL enviarse
únicamente al host de la URL del fichero de credenciales.

#### Scenario: La API redirige a otro host
- **WHEN** el servidor de la URL configurada responde 302 hacia otro host
- **THEN** el hook no hace ninguna segunda petición, el otro host no recibe nada y el comando de git
  termina con éxito
