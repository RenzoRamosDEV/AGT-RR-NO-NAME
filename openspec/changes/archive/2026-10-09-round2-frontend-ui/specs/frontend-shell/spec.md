## ADDED Requirements

### Requirement: Estados de carga, error y vacío
Las páginas que dependen de datos (canal, detalle y la navegación de proyectos) SHALL mostrar un
estado de carga mientras esperan, un mensaje de error con una acción «Reintentar» si la petición
falla, y un estado vacío o «no encontrado» (404) cuando no hay datos. Sin `VITE_API_URL` SHALL
usar datos de ejemplo.

#### Scenario: Error recuperable
- **WHEN** la petición del canal falla y el usuario pulsa «Reintentar» con la API ya disponible
- **THEN** el canal muestra los changes y desaparece el mensaje de error

#### Scenario: Proyecto inexistente
- **WHEN** la API responde 404 al pedir el canal
- **THEN** se muestra «Proyecto no encontrado» y no un error genérico

### Requirement: Cargar más changes
El canal SHALL ofrecer «Cargar más» mientras el servidor devuelva `next_cursor`, SHALL añadir la
página siguiente sin repetir changes ya mostrados, SHALL mantener la búsqueda y el filtro de
estado, SHALL reiniciar la lista al cambiar el filtro por tipo o de proyecto, y SHALL conservar
lo ya mostrado si la carga adicional falla.

#### Scenario: Página siguiente sin duplicados
- **WHEN** el servidor devuelve un change ya mostrado en la página siguiente
- **THEN** aparece una sola vez y «Cargar más» desaparece si no hay más cursor

#### Scenario: Fallo al cargar más
- **WHEN** falla la carga de la página siguiente
- **THEN** se mantienen los changes mostrados y se avisa del error con opción de reintentar

### Requirement: Filtro por estado de review
El canal SHALL ofrecer los filtros Todos, En curso, Con fallos y Completados, combinables con la
búsqueda y el filtro por tipo. Un change sin información de reviews SHALL aparecer solo en Todos.

#### Scenario: Filtrar con fallos
- **WHEN** el usuario elige «Con fallos»
- **THEN** solo se listan los changes con al menos una review fallida

### Requirement: Panel de hallazgos
El detalle de un change SHALL agrupar los hallazgos de todas sus reviews por archivo, ordenados
por severidad y línea, indicando severidad (con texto), agente y línea. Si no hay hallazgos no
SHALL mostrar el panel.

#### Scenario: Hallazgos de dos agentes en el mismo archivo
- **WHEN** dos agentes reportan hallazgos en el mismo archivo
- **THEN** aparecen bajo un único encabezado de archivo, el más grave primero, cada uno con su agente

### Requirement: Acciones del change
El detalle SHALL permitir abrir la URL del change en una pestaña nueva solo si es `http` o
`https`, y copiar el SHA completo y la rama al portapapeles, anunciando el resultado con texto y
funcionando también sin Clipboard API.

#### Scenario: URL no segura
- **WHEN** la URL del change usa un esquema distinto de `http` o `https`
- **THEN** no se muestra el enlace «Abrir»

#### Scenario: Copiar el SHA
- **WHEN** el usuario pulsa «Copiar SHA»
- **THEN** el portapapeles contiene el SHA completo y se anuncia «Copiado»
