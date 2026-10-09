# frontend-shell Specification

## Purpose
Define la apariencia y navegación base de la interfaz web de Duelo: un tema negro único,
una estructura de canales por proyecto y una representación clara de los estados de review.

## Requirements

### Requirement: Tema negro único
La interfaz SHALL renderizarse siempre con un tema negro, independientemente de la preferencia
de color del sistema, sin parpadeo de otro tema en la carga.

#### Scenario: Sistema en modo claro
- **WHEN** el navegador declara `prefers-color-scheme: light` y se abre la aplicación
- **THEN** el fondo y las superficies son negros desde el primer pintado

### Requirement: Navegación por canales
La interfaz SHALL mostrar una barra lateral con un canal por proyecto y una sección General con
enlaces a Estadísticas y Ajustes, y SHALL marcar el destino activo.

#### Scenario: Abrir un canal
- **WHEN** el usuario selecciona un proyecto en la barra lateral
- **THEN** la ruta es `/p/:slug` y el canal aparece marcado como activo

### Requirement: Hilos de reviews desplegables
Cada change del canal SHALL permitir desplegar sus reviews por agente, exponiendo su estado
con `aria-expanded` y operable con teclado.

#### Scenario: Desplegar con teclado
- **WHEN** el usuario enfoca "Ver respuestas" y pulsa Enter
- **THEN** se muestran las reviews de cada agente y `aria-expanded` pasa a `true`

### Requirement: Estado de review en curso
Una review en curso SHALL mostrar una animación de carga de IA; una completada o fallida SHALL
mostrarse sin animación y con indicación textual del estado.

#### Scenario: Review en curso
- **WHEN** una review está en estado "en curso"
- **THEN** se muestra un indicador animado de "pensando" y un borde animado

#### Scenario: Movimiento reducido
- **WHEN** el usuario tiene `prefers-reduced-motion: reduce`
- **THEN** las animaciones de carga se sustituyen por un indicador estático con texto

### Requirement: Contraste accesible
El texto y los controles interactivos SHALL cumplir contraste WCAG AA sobre el fondo negro.

#### Scenario: Texto secundario
- **WHEN** se muestra texto atenuado sobre una superficie
- **THEN** su ratio de contraste es al menos 4.5:1

### Requirement: Navegación adaptable
En pantallas estrechas la barra lateral SHALL ocultar sus enlaces tras un botón "Menú" que
exponga su estado con `aria-expanded`, SHALL cerrarse al navegar o al pulsar Escape, y SHALL
mantener los enlaces operables con teclado.

#### Scenario: Abrir y cerrar el menú
- **WHEN** el usuario activa el botón "Menú"
- **THEN** `aria-expanded` pasa a `true` y, al pulsar Escape, vuelve a `false`

#### Scenario: Navegar con el menú abierto
- **WHEN** el menú está abierto y el usuario sigue un enlace
- **THEN** la ruta cambia y el menú queda cerrado

### Requirement: Búsqueda en el canal
El canal SHALL ofrecer un campo de búsqueda que filtre los changes por título, autor o SHA sin
distinguir mayúsculas, combinado con el filtro por tipo, y SHALL indicar cuando no hay
coincidencias.

#### Scenario: Buscar por SHA
- **WHEN** el usuario escribe parte del SHA de un change
- **THEN** solo se listan los changes cuyo SHA contiene ese texto

#### Scenario: Sin coincidencias
- **WHEN** ningún change cumple la búsqueda y el filtro
- **THEN** se muestra "Ningún cambio coincide con la búsqueda."

### Requirement: Resumen de reviews por change
Cada change del canal SHALL mostrar, sin desplegar el hilo, cuántas reviews están completadas,
en curso o fallidas, con texto además de color.

#### Scenario: Change con reviews mixtas
- **WHEN** un change tiene una review completada y otra en curso
- **THEN** su card muestra "1 completada" y "1 en curso"

### Requirement: Diff legible
El detalle de un change SHALL mostrar el diff con líneas numeradas, la cabecera de archivo
diferenciada y las líneas añadidas o borradas distinguibles sin depender solo del color, y SHALL
avisar cuando el diff está truncado.

#### Scenario: Diff con añadidos y borrados
- **WHEN** se abre un change con líneas `+` y `-`
- **THEN** cada línea muestra su número y las añadidas y borradas llevan una marca textual

#### Scenario: Diff truncado
- **WHEN** el change tiene el diff truncado
- **THEN** se muestra un aviso de que solo se ve una parte del diff

### Requirement: Estadísticas con barras compactas
La página de estadísticas SHALL acompañar `% útiles`, duración y fallos con una barra
proporcional decorativa, manteniendo el valor numérico en la tabla.

#### Scenario: Valor accesible
- **WHEN** un lector de pantalla recorre la tabla
- **THEN** lee el valor numérico de cada celda y las barras no se anuncian

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

### Requirement: Navegador de archivos del diff
El detalle de un change SHALL mostrar, si el diff tiene archivos identificables, una lista de los
archivos tocados con sus líneas añadidas y borradas y enlaces que saltan a la sección de cada
archivo. SHALL reconocer cabeceras `@@ <archivo>` y `diff --git`, y no SHALL contar las líneas de
metadatos (`index`, `---`, `+++`) como cambios.

#### Scenario: Dos archivos
- **WHEN** el diff toca `a.py` (+2 −1) y `b.py` (+1 −0)
- **THEN** la lista muestra ambos archivos con «+2 −1» y «+1 −0» y cada uno enlaza a su sección

#### Scenario: Diff estilo git
- **WHEN** el diff contiene `--- a/x`, `+++ b/x` y un hunk con una línea añadida
- **THEN** el recuento del archivo es +1 −0

### Requirement: Ordenación de estadísticas
La tabla de estadísticas SHALL poder ordenarse por cada columna mediante botones en las
cabeceras, SHALL indicar la columna y el sentido activos con `aria-sort` y SHALL invertir el
sentido al volver a pulsar la misma columna.

#### Scenario: Ordenar por fallos
- **WHEN** el usuario pulsa la cabecera «Fallos»
- **THEN** las filas quedan ordenadas por fallos ascendente y la cabecera indica `aria-sort="ascending"`

#### Scenario: Invertir el sentido
- **WHEN** el usuario pulsa «Fallos» dos veces
- **THEN** el orden es descendente y `aria-sort="descending"`

### Requirement: Antigüedad de los changes
Cada change del canal SHALL mostrar su antigüedad relativa («hace 12 min») en un elemento `<time>`
con la fecha absoluta en `datetime` y `title`. Si el change no tiene fecha SHALL omitirla.

#### Scenario: Cambio reciente
- **WHEN** un change se creó hace 12 minutos
- **THEN** se muestra «hace 12 min» y el `datetime` contiene la fecha ISO original

### Requirement: Vista compacta del canal
El canal SHALL ofrecer un interruptor entre tarjetas y filas compactas, conservando búsqueda,
filtros y la posibilidad de ver las respuestas de cada change.

#### Scenario: Cambiar a compacta
- **WHEN** el usuario pulsa «Compacta»
- **THEN** los changes se listan en filas, el botón queda con `aria-pressed="true"` y los filtros se mantienen

### Requirement: Estado vacío accionable
Un canal sin changes y sin filtros activos SHALL mostrar el comando mínimo para ingestar un commit
del proyecto, usando un token de ejemplo y nunca uno real, con un botón para copiarlo.

#### Scenario: Proyecto sin changes
- **WHEN** se abre un proyecto sin changes
- **THEN** se muestra un comando que incluye el slug del proyecto y `$INGEST_TOKEN`
