## MODIFIED Requirements

### Requirement: Búsqueda en el canal
El canal SHALL ofrecer un campo de búsqueda que filtre los changes por título, autor, SHA o ref
sin distinguir mayúsculas, combinado con el filtro por tipo y el de estado, y SHALL indicar cuando
no hay coincidencias. La búsqueda SHALL resolverse en el servidor (parámetro `q`), no sobre lo ya
cargado.

#### Scenario: Buscar por SHA
- **WHEN** el usuario escribe parte del SHA de un change
- **THEN** solo se listan los changes cuyo SHA contiene ese texto

#### Scenario: Sin coincidencias
- **WHEN** ningún change cumple la búsqueda y el filtro
- **THEN** se muestra "Ningún cambio coincide con la búsqueda."

### Requirement: Resumen de reviews por change
Cada change del canal SHALL mostrar, sin desplegar el hilo, cuántas reviews están completadas,
en curso o fallidas, con texto además de color. Si la fuente no trae las reviews pero sí el estado
agregado (`review_status`), SHALL mostrar ese estado como insignia de texto.

#### Scenario: Change con reviews mixtas
- **WHEN** un change tiene una review completada y otra en curso
- **THEN** su card muestra "1 completada" y "1 en curso"

#### Scenario: Solo estado agregado
- **WHEN** el listado de la API trae `review_status: "partial_failed"` y ninguna review
- **THEN** la card muestra la insignia "Fallo parcial"

### Requirement: Estadísticas con barras compactas
La página de estadísticas SHALL acompañar la duración media y los fallos con una barra
proporcional decorativa, manteniendo el valor numérico en la tabla.

#### Scenario: Valor accesible
- **WHEN** un lector de pantalla recorre la tabla
- **THEN** lee el valor numérico de cada celda y las barras no se anuncian

### Requirement: Filtro por estado de review
El canal SHALL ofrecer los filtros Todos, En curso, Con fallos y Completados, combinables con la
búsqueda y el filtro por tipo, y SHALL aplicarlos en el servidor: «En curso» pide los estados
`pending` y `running`, «Con fallos» pide `failed` y `partial_failed` y «Completados» pide
`completed`; «Todos» no envía ningún estado.

#### Scenario: Filtrar con fallos
- **WHEN** el usuario elige «Con fallos»
- **THEN** la petición lleva `status=failed&status=partial_failed` y solo se listan los changes devueltos

## ADDED Requirements

### Requirement: Filtros del canal en servidor
El canal SHALL enviar al servidor la búsqueda (`q`), el tipo (`kind`), el estado (`status`) y el
cursor, SHALL reiniciar la lista y el cursor al cambiar cualquiera de los filtros o de proyecto, y
NO SHALL mezclar changes de una petición obsoleta con los de la vigente. La búsqueda SHALL
enviarse con un breve retardo tras dejar de escribir y recortada de espacios; una búsqueda vacía
NO SHALL enviar `q`.

#### Scenario: Parámetros enviados
- **WHEN** el usuario escribe "fix", elige «PRs» y «Con fallos»
- **THEN** la petición lleva `q=fix`, `kind=pr` y `status` de los estados con fallo

#### Scenario: Cursor reiniciado
- **WHEN** el usuario ha cargado una segunda página y cambia el filtro de estado
- **THEN** la nueva petición no lleva cursor y solo se muestran sus resultados

#### Scenario: Respuesta obsoleta
- **WHEN** llega la respuesta de un filtro anterior después de la del filtro vigente
- **THEN** la lista conserva solo los resultados del filtro vigente

### Requirement: Estadísticas reales por agente
La página de estadísticas SHALL consumir las estadísticas por agente de la API (total, completadas,
fallidas, duración media y nota media), SHALL mostrar un estado de carga, un error con
«Reintentar» y un estado vacío, y SHALL mostrar «—» cuando una media no tenga datos, ordenando
esos valores siempre al final.

#### Scenario: Datos de la API
- **WHEN** la API devuelve dos agentes con sus totales
- **THEN** la tabla muestra una fila por agente con total, completadas, fallos, duración y nota

#### Scenario: Sin datos
- **WHEN** la API devuelve una lista vacía
- **THEN** se muestra "Aún no hay reviews registradas."

#### Scenario: Error recuperable
- **WHEN** la petición falla y el usuario pulsa «Reintentar» con la API disponible
- **THEN** se muestra la tabla y desaparece el error

#### Scenario: Media sin datos
- **WHEN** un agente tiene `avg_score` nulo
- **THEN** su celda muestra «—» y al ordenar por nota queda al final en ambos sentidos

### Requirement: Reintentar una review fallida
El detalle de un change SHALL ofrecer «Reintentar review» solo cuando su estado agregado es
`failed` o `partial_failed`. El token de ingesta SHALL escribirlo el usuario en un campo de
contraseña y SHALL conservarse únicamente en memoria de la pestaña: NO SHALL guardarse en
`localStorage`, en la URL ni en el código compilado. La acción SHALL tratar los resultados 202
(avisa del nuevo run y recarga el detalle), 401 (token no válido, lo olvida), 404, 409 (ya no se
puede reintentar, recarga el detalle), 503 (orquestador no disponible) y los fallos de red, y SHALL
admitir un solo envío a la vez.

#### Scenario: Visible solo con fallo
- **WHEN** el estado agregado del change es `completed`, `running` o `pending`
- **THEN** no hay botón de reintento

#### Scenario: Reintento aceptado
- **WHEN** el usuario escribe el token y pulsa «Reintentar review» y la API responde 202 con `run: 2`
- **THEN** se avisa "Reintento en marcha (run 2)" y se recarga el detalle

#### Scenario: Token no válido
- **WHEN** la API responde 401
- **THEN** se muestra "Token de ingesta no válido" y el campo vuelve a quedar vacío

#### Scenario: Conflicto
- **WHEN** la API responde 409
- **THEN** se avisa de que la review ya no se puede reintentar y se recarga el detalle

#### Scenario: Orquestador caído
- **WHEN** la API responde 503
- **THEN** se avisa de que el orquestador no está disponible y se puede volver a intentar

#### Scenario: El token no se persiste
- **WHEN** el usuario envía un reintento con un token
- **THEN** el token no aparece en `localStorage` ni en `sessionStorage`

### Requirement: Diagnóstico del servidor en Ajustes
Ajustes SHALL mostrar los proyectos vigilados de la API y el estado de cada dependencia (Postgres
y Temporal) con su latencia, el estado global (correcto o degradado) y, si falla, el motivo
traducido (`timeout` o `error`), con un botón «Actualizar». Un fallo al cargar los proyectos NO
SHALL ocultar el diagnóstico ni viceversa, y NO SHALL mostrarse texto libre procedente del
servidor.

#### Scenario: Todo disponible
- **WHEN** ambas dependencias responden
- **THEN** se muestra el estado correcto y la latencia de cada una

#### Scenario: Dependencia degradada
- **WHEN** Temporal responde `unavailable` con `reason: "timeout"`
- **THEN** se muestra el estado degradado y "Tiempo agotado" para Temporal

#### Scenario: Fallo parcial
- **WHEN** falla la carga del diagnóstico pero la de proyectos funciona
- **THEN** se muestran los proyectos y un error recuperable solo en el diagnóstico

### Requirement: Metadatos de cada review
Cada review SHALL mostrar su run, su duración y su nota cuando existan, y las fallidas SHALL
mostrar su motivo sanitizado: sin caracteres de control, con valores que parezcan secretos
ocultos y recortado a una longitud razonable, siempre como texto.

#### Scenario: Review completada con datos
- **WHEN** una review completada tiene `run: 2`, 42 s y nota 8
- **THEN** su card muestra "Run 2", "42 s" y "Nota 8"

#### Scenario: Error con secreto
- **WHEN** una review fallida trae el error "boom token=abc123 en la llamada"
- **THEN** la card muestra el motivo con el valor del token oculto
