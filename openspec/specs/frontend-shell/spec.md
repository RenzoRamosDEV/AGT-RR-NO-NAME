# frontend-shell Specification

## Purpose
Define la apariencia y navegación base de la interfaz web de Duelo: un tema negro único,
una estructura de canales por proyecto y una representación clara de los estados de review.

## Requirements

### Requirement: Navegación por canales
La interfaz SHALL mostrar una barra lateral con un canal por proyecto y una sección General con
enlaces a Estadísticas y Ajustes, y SHALL marcar el destino activo con el color de énfasis.

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
Una review en curso SHALL mostrarse como un mensaje con el orbe de «pensando» y su etiqueta; una
completada o fallida SHALL mostrarse sin animación y con indicación textual del estado.

#### Scenario: Review en curso
- **WHEN** una review está en estado "en curso"
- **THEN** se muestra un indicador animado de "pensando" con el nombre del agente

#### Scenario: Movimiento reducido
- **WHEN** el usuario tiene `prefers-reduced-motion: reduce`
- **THEN** las animaciones de carga y las transiciones se desactivan y el orbe se sustituye por un
  indicador estático con texto

### Requirement: Contraste accesible
El texto y los controles interactivos SHALL cumplir contraste WCAG AA en el tema claro y en el
oscuro: el texto atenuado sobre cada superficie, los colores de estado sobre las superficies y
sobre sus fondos tintados, el botón principal (normal y con el cursor encima), el elemento
seleccionado de la barra lateral y el texto sobre los fondos del diff.

#### Scenario: Texto secundario
- **WHEN** se muestra texto atenuado sobre una superficie, en cualquiera de los dos temas
- **THEN** su ratio de contraste es al menos 4.5:1

#### Scenario: Estados sobre su fondo
- **WHEN** se muestra un estado (éxito, fallo, aviso) sobre su fondo tintado
- **THEN** su ratio de contraste es al menos 4.5:1 en ambos temas

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
La página de estadísticas SHALL acompañar la duración media y los fallos con una barra
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
búsqueda y el filtro por tipo, y SHALL aplicarlos en el servidor: «En curso» pide los estados
`pending` y `running`, «Con fallos» pide `failed` y `partial_failed` y «Completados» pide
`completed`; «Todos» no envía ningún estado.

#### Scenario: Filtrar con fallos
- **WHEN** el usuario elige «Con fallos»
- **THEN** la petición lleva `status=failed&status=partial_failed` y solo se listan los changes devueltos

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

### Requirement: Navegación con slugs owner/repo
La interfaz SHALL servir el canal de un proyecto en `/p/<slug>` y el detalle de un change en
`/p/<slug>/changes/<id>`, donde `<slug>` puede tener varios segmentos (`owner/repo`). Todos los
enlaces internos a un proyecto o a un change SHALL construirse con un único helper que codifique
cada segmento.

#### Scenario: Canal de un proyecto con barra
- **WHEN** el usuario abre `/p/acme/widgets`
- **THEN** se muestra el canal de `acme/widgets`

#### Scenario: Detalle de un change de un proyecto con barra
- **WHEN** el usuario abre `/p/acme/widgets/changes/c1`
- **THEN** se muestra el detalle del change `c1`, con una miga que enlaza a `/p/acme/widgets`

#### Scenario: Entrada por la raíz
- **WHEN** el usuario abre `/` y el primer proyecto es `acme/widgets`
- **THEN** la interfaz redirige a `/p/acme/widgets` y muestra su canal

#### Scenario: Slug de un solo segmento
- **WHEN** el usuario abre `/p/duelo`
- **THEN** se muestra el canal de `duelo`

### Requirement: Página no encontrado
Una URL que no corresponda a ninguna página SHALL mostrar un mensaje «No encontrado» con un
enlace al inicio, dentro de la estructura habitual, y SHALL NOT dejar la página en blanco.

#### Scenario: Ruta desconocida
- **WHEN** el usuario abre `/nada`
- **THEN** se muestra «No encontrado» y un enlace al inicio

#### Scenario: Proyecto sin slug
- **WHEN** el usuario abre `/p`
- **THEN** se muestra «No encontrado»

### Requirement: Hallazgos sin ubicación
El panel de hallazgos y las cards de review SHALL NOT mostrar un archivo vacío o `N/A` ni una
línea no positiva. Los hallazgos sin archivo SHALL agruparse bajo «Sin archivo», siempre al final,
y conservar el orden por severidad.

#### Scenario: Hallazgo sin archivo ni línea
- **WHEN** una review trae un hallazgo con archivo `N/A` y línea `0`
- **THEN** el panel lo muestra bajo «Sin archivo» sin `N/A` ni `L0`

#### Scenario: Grupo sin archivo al final
- **WHEN** hay hallazgos con archivo y otros sin él
- **THEN** el grupo «Sin archivo» aparece después de todos los grupos con archivo

#### Scenario: Card con hallazgo sin ubicación
- **WHEN** una card de review lista un hallazgo sin archivo ni línea
- **THEN** muestra el mensaje sin la ubicación

### Requirement: Nombre de agente fiel
La interfaz SHALL mostrar el nombre real del agente de cada review. Solo `claude` y `codex`
SHALL tener nombre propio («Claude», «Codex»); cualquier otro agente SHALL mostrarse con su
nombre y un avatar de iniciales neutro, y SHALL NOT atribuirse a Claude.

#### Scenario: Agente desconocido
- **WHEN** una review llega con el agente `agent_1`
- **THEN** la card muestra «Agent_1» y un avatar «A1», no «Claude»

#### Scenario: Agente conocido
- **WHEN** una review llega con el agente `codex`
- **THEN** la card muestra «Codex»

### Requirement: Añadir un proyecto desde una carpeta local
La interfaz SHALL ofrecer un botón «Añadir proyecto» en la barra lateral y en el estado vacío que
abre un diálogo accesible (`role` de diálogo, foco inicial en el campo de ruta, Tab sin salir del
diálogo, Escape lo cierra y el foco vuelve al botón que lo abrió). El diálogo SHALL pedir la ruta
absoluta del repositorio y el token de ingesta (campo de contraseña, solo en memoria) y SHALL
avisar de que se instalarán hooks de git `post-commit` y `pre-push` en ese repositorio, que se
pueden desinstalar. Una ruta que no sea absoluta SHALL rechazarse sin llamar a la API.

#### Scenario: Alta correcta
- **WHEN** el usuario escribe una ruta válida y el token y pulsa «Añadir»
- **THEN** el proyecto aparece en la barra lateral, queda seleccionado y el diálogo se cierra

#### Scenario: Función desactivada
- **WHEN** la API responde 404
- **THEN** el diálogo explica que la función está desactivada y que debe arrancarse con
  `LOCAL_PROJECTS_ENABLED=true`

#### Scenario: Proyecto ya añadido
- **WHEN** la API responde 409
- **THEN** el diálogo indica que el proyecto ya está añadido

#### Scenario: Ruta que no es un repositorio
- **WHEN** la API responde 422
- **THEN** el diálogo indica que la ruta no es un repositorio git válido

#### Scenario: Token no válido
- **WHEN** la API responde 401
- **THEN** el diálogo pide un token válido y el token guardado en memoria se olvida

#### Scenario: Ruta relativa
- **WHEN** el usuario escribe una ruta que no empieza por `/` ni por una unidad de disco
- **THEN** se muestra un error en el diálogo y no se envía ninguna petición

### Requirement: Gestión de proyectos en Ajustes
Ajustes SHALL listar cada proyecto con su nombre, su ruta y el estado de sus hooks. Para los
proyectos con repositorio en GitHub SHALL ofrecer «Sincronizar PRs», que muestra cuántas PRs se
sincronizaron y cuántas son nuevas, o el motivo del fallo (el 503 indica que falta `gh`). SHALL
ofrecer «Quitar proyecto» con una confirmación explícita que avise de que se borra su historial y
con el foco inicial en «Cancelar».

#### Scenario: Lista con ruta y hooks
- **WHEN** hay un proyecto con ruta y hooks instalados
- **THEN** Ajustes muestra su ruta y «Hooks instalados»

#### Scenario: Sincronizar PRs
- **WHEN** el usuario pulsa «Sincronizar PRs» en un proyecto de GitHub
- **THEN** se muestra «2 PRs sincronizadas (1 nueva)» o el equivalente con los números devueltos

#### Scenario: Sincronizar sin `gh`
- **WHEN** la API responde 503 con un motivo
- **THEN** Ajustes muestra ese motivo

#### Scenario: Proyecto sin GitHub
- **WHEN** un proyecto no tiene repositorio en GitHub
- **THEN** no se ofrece «Sincronizar PRs»

#### Scenario: Quitar con confirmación
- **WHEN** el usuario pulsa «Quitar proyecto»
- **THEN** se abre una confirmación que avisa de que se borra el historial y no se borra nada
  hasta que el usuario la confirma

### Requirement: Auto-actualización
La barra lateral, el canal y el detalle de un change SHALL refrescarse solos cada pocos segundos
sin recargar la página, de modo que un commit o una PR nuevos aparezcan solos. El refresco SHALL
ser silencioso (sin estado de carga ni parpadeo), SHALL pausarse mientras la pestaña esté oculta y
refrescar al volver a mostrarla, SHALL conservar la búsqueda, los filtros y los elementos cargados
con «Cargar más» (sin perder ni duplicar ninguno) y SHALL NOT solapar peticiones. El detalle SHALL
seguir refrescándose solo mientras la review no haya terminado. La interfaz SHALL mostrar de forma
discreta cuándo se actualizó por última vez y avisar si el último refresco falló, conservando los
datos anteriores.

#### Scenario: Aparece un commit nuevo
- **WHEN** llega un commit nuevo mientras el canal está abierto
- **THEN** aparece en la lista sin recargar y sin mostrar «Cargando»

#### Scenario: Se conservan búsqueda y páginas cargadas
- **WHEN** hay un texto de búsqueda y se han cargado más páginas y llega un refresco con un
  elemento nuevo
- **THEN** la búsqueda y todos los elementos cargados siguen visibles, cada uno una sola vez

#### Scenario: Pestaña oculta
- **WHEN** la pestaña está oculta
- **THEN** no se hacen peticiones, y al volver a mostrarse se refresca de inmediato

#### Scenario: Fallo al refrescar
- **WHEN** un refresco falla
- **THEN** los datos anteriores siguen visibles y se indica que la actualización falló

#### Scenario: Detalle terminado
- **WHEN** la review de un change ya terminó
- **THEN** el detalle deja de refrescarse

### Requirement: Respuestas del canal con la API real
El canal SHALL mostrar en «Ver respuestas» las reviews ligeras que trae el listado (agente, estado,
nota y duración) de inmediato, y SHALL pedir el detalle completo del change (`GET /changes/{id}`)
al abrir el hilo cuando alguna review sea ligera, para mostrar resumen, hallazgos y motivo del fallo.
Mientras carga SHALL indicarlo; si falla SHALL avisar sin perder las reviews ligeras y ofrecer
«Reintentar». Un change sin reviews SHALL conservar en su resumen el badge del estado agregado en
lugar de quedarse vacío, y su hilo SHALL decir que aún no hay respuestas.

#### Scenario: Se abre un hilo
- **WHEN** el usuario abre «Ver respuestas» de un change con reviews ligeras
- **THEN** ve al instante los agentes con su estado, y cuando llega el detalle ve sus resúmenes y
  hallazgos

#### Scenario: El detalle falla
- **WHEN** el detalle del change falla al abrir el hilo
- **THEN** las reviews ligeras siguen visibles, aparece un aviso y «Reintentar» vuelve a pedirlo

#### Scenario: Reviews ya completas
- **WHEN** las reviews del change ya traen su resumen (datos de ejemplo)
- **THEN** no se pide el detalle

### Requirement: Agentes configurados en la interfaz
La interfaz SHALL tomar los nombres de los agentes de `agent_names` del diagnóstico del servidor y
mostrarlos con su nombre real (Claude y Codex con su nombre propio, cualquier otro tal cual
capitalizado) en la cabecera del canal, en el estado vacío y en Ajustes. NUNCA SHALL suponer
«Claude y Codex» ni un número fijo de agentes: mientras los agentes se desconocen (carga o fallo del
diagnóstico) el texto SHALL decir «los agentes configurados», y Ajustes SHALL mostrar un guion si el
servidor no informa de ninguno. El estado agregado de los datos de ejemplo SHALL calcularse con el
número de agentes de su propio diagnóstico.

#### Scenario: Agentes distintos de Claude y Codex
- **WHEN** el servidor informa `agent_names` = `agent_1`, `agent_2` y `gemini`
- **THEN** el canal dice «revisados por Agent_1, Agent_2 y Gemini» y Ajustes lista esos tres, sin
  mencionar a Claude

#### Scenario: Agentes desconocidos
- **WHEN** el diagnóstico falla o aún no ha respondido
- **THEN** el canal dice «revisados por los agentes configurados» sin nombrar ninguno

### Requirement: Detalle del run actual
El detalle de un change SHALL mostrar en las cards principales y en el panel de hallazgos solo las
reviews de su `run` actual (una review sin `run` cuenta como run 1), igual que el backend para su
estado y su resumen de hallazgos. Las reviews de runs anteriores SHALL mostrarse en secciones
colapsadas (`<details>`), una por run, de la más reciente a la más antigua, con el número de run y
de reviews en el título. Sin runs anteriores no SHALL haber sección colapsada.

#### Scenario: Tras un reintento
- **WHEN** el detalle de un change en el run 2 incluye reviews del run 1 y del run 2
- **THEN** el panel de hallazgos y las cards principales solo muestran las del run 2, y las del run 1
  quedan colapsadas bajo «Run 1 (anterior)»

#### Scenario: Un solo run
- **WHEN** todas las reviews son del run actual
- **THEN** no aparece ninguna sección colapsada

### Requirement: Indicador de carga con orbes
Toda carga o acción en curso de la interfaz SHALL mostrar un orbe de `thinking-orbs` de 20 px, con
el tema vigente (claro u oscuro), junto a una etiqueta de texto visible, sin cambiar la maquetación
(el orbe reserva su hueco). El estado del orbe SHALL depender de la actividad: cargas de listas,
páginas, proyectos, detalle y estadísticas `searching`; «Cargar más» y agentes revisando `working`;
reintento de una review `solving`; añadir, quitar o sincronizar proyectos y el diagnóstico
`connecting`. El indicador SHALL ser accesible (región de estado anunciada con la etiqueta; el orbe
es decorativo) y, con `prefers-reduced-motion`, SHALL sustituir el orbe animado por un «…» estático
sin montar ningún canvas.

#### Scenario: Carga de una página
- **WHEN** el canal, el detalle, las estadísticas, los proyectos o el diagnóstico están cargando
- **THEN** se muestra su etiqueta («Cargando cambios…», «Comprobando dependencias…», etc.) con un
  orbe del estado que le corresponde

#### Scenario: Acción en curso en un botón
- **WHEN** el usuario envía «Reintentar review», «Añadir», «Quitar proyecto» o «Sincronizar PRs», o
  pulsa «Cargar más» y la petición está en curso
- **THEN** el botón queda deshabilitado y su texto lleva un orbe en línea del estado de esa acción

#### Scenario: Movimiento reducido
- **WHEN** el usuario prefiere movimiento reducido
- **THEN** ninguna carga monta un canvas animado y todas conservan su etiqueta de texto

#### Scenario: Sondeo silencioso
- **WHEN** una página se refresca sola por el sondeo
- **THEN** no aparece ningún orbe y los datos anteriores siguen visibles

#### Scenario: Tema claro
- **WHEN** el tema vigente es el claro
- **THEN** el orbe se dibuja con la tinta oscura del tema claro

### Requirement: Agentes pendientes de un change
Las tarjetas del canal y el detalle de un change con estado agregado `pending` o `running` SHALL
mostrar un orbe `working` con el nombre de cada agente esperado (`agent_names` del diagnóstico) que
aún no tiene review del run actual, y SHALL retirarlo cuando esa review llega. Un agente con review
de un run anterior SHALL seguir contando como pendiente en el run actual. Mientras los agentes
esperados no se conozcan, SHALL mostrarse un único orbe genérico en lugar de inventar nombres. Un
change `completed`, `failed` o `partial_failed` no SHALL mostrar agentes pendientes.

#### Scenario: Ninguna review todavía
- **WHEN** un change `pending` tiene agentes esperados `agent_1` y `agent_2` y ninguna review
- **THEN** se muestran dos orbes, «Agent_1 está revisando…» y «Agent_2 está revisando…»

#### Scenario: Review parcial
- **WHEN** `agent_1` ya entregó su review y `agent_2` no
- **THEN** solo queda el orbe de `agent_2`

#### Scenario: Todos entregaron
- **WHEN** el change pasa a `completed`
- **THEN** no queda ningún orbe de agente pendiente

#### Scenario: Reintento
- **WHEN** un change tiene reviews del run 1 y está `pending` en el run 2
- **THEN** ambos agentes figuran como pendientes del run 2

#### Scenario: Agentes desconocidos
- **WHEN** el diagnóstico aún no ha informado de los agentes y el change está `pending`
- **THEN** se muestra un único orbe «Esperando a los agentes…»

### Requirement: Temas claro y oscuro
La interfaz SHALL ofrecer un tema oscuro (por defecto) y uno claro, definidos como tokens CSS, y un
selector Sistema / Claro / Oscuro en la cabecera y en Ajustes que SHALL permanecer sincronizado.
«Sistema» SHALL seguir `prefers-color-scheme`, también cuando cambie con la página abierta. El tema
SHALL fijarse antes del primer pintado, sin parpadeo del otro, y lo único que se guarda es la
preferencia elegida (`localStorage`), nunca datos del usuario.

#### Scenario: Sistema en modo claro
- **WHEN** no hay preferencia guardada y el navegador declara `prefers-color-scheme: light`
- **THEN** la página se pinta en el tema claro desde el primer fotograma

#### Scenario: Elegir un tema
- **WHEN** el usuario pulsa «Oscuro» en Ajustes
- **THEN** `<html data-theme>` pasa a `dark`, se guarda `duelo-theme=dark` y el selector de la
  cabecera marca también el oscuro

#### Scenario: Volver a Sistema
- **WHEN** el usuario pulsa «Sistema»
- **THEN** se borra la preferencia guardada y el tema vuelve a seguir al sistema operativo

#### Scenario: Almacenamiento bloqueado
- **WHEN** `localStorage` no se puede escribir
- **THEN** el tema cambia igualmente y la elección dura hasta cerrar la página

### Requirement: Marco de la aplicación
La interfaz SHALL tener una barra superior con la marca (enlace al inicio) y el selector de tema, y
una barra lateral estilo Slack con la sección Proyectos como lista de canales (`#`), colapsable con
`aria-expanded`, una acción «Añadir proyecto» y la sección General. En pantallas estrechas la barra
lateral SHALL ser un cajón con velo que se cierra con Escape, con el velo o al navegar, y sus
enlaces no SHALL ser alcanzables con Tab mientras esté cerrado.

#### Scenario: Colapsar los proyectos
- **WHEN** el usuario pulsa «Proyectos» en la barra lateral
- **THEN** la lista de canales se oculta, `aria-expanded` pasa a `false` y los enlaces de General
  siguen disponibles

#### Scenario: Orden de tabulación
- **WHEN** el usuario recorre la página con Tab
- **THEN** pasa por el menú, la marca, el selector de tema, la barra lateral y la página

### Requirement: Lista de changes estilo PR
El canal SHALL listar sus changes como la lista de PRs de GitHub: un icono de estado con texto
alternativo (pendiente, en curso, fallo parcial, fallida, completada), el título enlazado en
negrita, `#sha · por autor · antigüedad`, una etiqueta Commit o PR y, a la derecha, un «check» por
agente con su estado como texto. La cabecera de la lista SHALL ofrecer el filtro de estado como
pestañas y contar lo **cargado** por estado, añadiendo «+» cuando haya otra página.

#### Scenario: Estado con texto alternativo
- **WHEN** se muestra un change con `review_status` `partial_failed`
- **THEN** su icono es una imagen con el texto «Fallo parcial»

#### Scenario: Checks de los agentes
- **WHEN** un change tiene reviews de `agent_1` (completada) y `agent_2` (fallida)
- **THEN** la fila muestra dos checks con los nombres «Agent_1: completada» y «Agent_2: fallida»

#### Scenario: Sin reviews todavía
- **WHEN** un change aún no tiene ninguna review
- **THEN** la fila no muestra checks y sí los agentes pendientes

#### Scenario: Contadores de lo cargado
- **WHEN** hay tres changes cargados y hay otra página
- **THEN** la cabecera dice «3+ cambios» seguido del desglose por estado

### Requirement: Reviews como mensajes
Cada review SHALL mostrarse como un mensaje de una app: avatar con color estable por agente,
nombre, etiqueta «APP», estado, resumen, hallazgos con una barra de color por severidad (rojo para
`critical`, `bug` y `high`; ámbar para `risk` y `medium`; neutro para el resto) y, como
«reacciones», el run, la duración y la nota. Dos agentes cuyos nombres solo difieren en un carácter
SHALL tener colores claramente distintos.

#### Scenario: Severidad con color
- **WHEN** una review tiene hallazgos `bug`, `risk` y `nit`
- **THEN** sus barras son roja, ámbar y neutra respectivamente

#### Scenario: Agente sin respuesta
- **WHEN** un agente esperado aún no ha entregado su review
- **THEN** aparece como un mensaje «escribiendo» con su orbe y «Agent_1 está revisando…»

### Requirement: Detalle como conversación
El detalle de un change SHALL organizarse en una cabecera con la píldora de estado (icono y texto),
la conversación de los agentes y «Archivos cambiados». Los hallazgos SHALL listarse una sola vez
en el panel agrupado por archivo (no repetidos dentro de los mensajes), las reviews SHALL salir
ordenadas por agente, y el diff SHALL mostrar una cabecera por archivo con `+N −M` y la barra de
cinco cuadrados (decorativa, oculta a los lectores de pantalla), cabeceras de hunk diferenciadas,
numeración y fondos distintos para líneas añadidas y borradas.

#### Scenario: Hallazgos sin duplicar
- **WHEN** se abre un change con un hallazgo
- **THEN** su mensaje aparece una vez en el panel de hallazgos y no dentro del mensaje del agente

#### Scenario: Barra de cuadrados
- **WHEN** un archivo tiene 8 líneas añadidas y 2 borradas
- **THEN** su barra tiene cuatro cuadrados verdes y uno rojo, y está oculta a la tecnología asistiva

### Requirement: Atajo de búsqueda
En el canal, pulsar «/» SHALL enfocar el buscador sin escribir la barra, salvo que el foco esté ya
en un campo de texto o haya un diálogo abierto.

#### Scenario: Pulsar «/»
- **WHEN** el usuario pulsa «/» con el foco fuera de un campo
- **THEN** el buscador recibe el foco y queda vacío

### Requirement: Ajustes en cajas
Ajustes SHALL organizarse en cajas con título (Apariencia, General, Proyectos vigilados,
Diagnóstico); Apariencia contiene el selector de tema y las acciones destructivas («Quitar
proyecto») se muestran en rojo y con confirmación.

#### Scenario: Cambiar el tema desde Ajustes
- **WHEN** el usuario elige «Claro» en la caja Apariencia
- **THEN** la interfaz pasa al tema claro

### Requirement: Tarjetas de resumen en estadísticas
Estadísticas SHALL mostrar, sobre la tabla, tarjetas con el total de reviews, completadas, con
fallo y las medias globales de duración y nota, ponderadas por las reviews de cada agente, con un
guion cuando nadie reporta la media.

#### Scenario: Medias ponderadas
- **WHEN** `agent_1` tiene 3 reviews con 1 s y `agent_2` 1 review con 5 s
- **THEN** la duración media mostrada es 2 s

### Requirement: Estados vacíos y de error con ilustración
Los estados vacíos, de error y de página no encontrada SHALL mostrar una ilustración decorativa, un
título, una explicación y la acción principal; mientras carga el canal SHALL verse una estructura
de esqueleto oculta a la tecnología asistiva junto al texto de carga.

#### Scenario: Página no encontrada
- **WHEN** se abre una dirección que no existe
- **THEN** se ve el título «No encontrado» como encabezado de la página y un botón «Volver al
  inicio»

### Requirement: Brillo de borde en lo que está en curso
Las filas del canal con estado agregado `pending` o `running` y el panel «Revisión de los agentes»
del detalle de un change en ese estado SHALL llevar un brillo ámbar que recorre su borde inferior
(`border-beam`). Un change `completed`, `failed` o `partial_failed` NO SHALL llevarlo. El brillo SHALL
ser decorativo (no sustituye al icono ni al texto de estado), SHALL leer el tema efectivo de la
aplicación y SHALL desaparecer cuando el change termina en el siguiente refresco. Con
`prefers-reduced-motion` NO SHALL animarse ni cargarse.

#### Scenario: Filas en curso y terminadas
- **WHEN** el canal lista cambios `pending`, `running`, `completed` y `failed`
- **THEN** solo las filas `pending` y `running` llevan el brillo

#### Scenario: El change termina
- **WHEN** un change con brillo pasa a `completed` en el siguiente refresco
- **THEN** la fila conserva su contenido y pierde el brillo

#### Scenario: Movimiento reducido
- **WHEN** el usuario prefiere movimiento reducido
- **THEN** ninguna fila ni panel se envuelve con el brillo

### Requirement: Selector de tema con indicador líquido
El selector Sistema/Claro/Oscuro SHALL pintarse primero como un control segmentado normal, usable de
inmediato, y SHALL mostrar el segmento activo como un indicador líquido que se desliza a la opción
elegida (`liquid-gooey`, efecto `move`) cuando la capa diferida está cargada. Los botones SHALL seguir
siendo botones reales (`aria-pressed`, nombre accesible) por encima del indicador, que SHALL ser
decorativo (`aria-hidden`). Con `prefers-reduced-motion` NO SHALL haber indicador y el botón pulsado
SHALL quedar teñido.

#### Scenario: Primer pintado
- **WHEN** se muestra el selector antes de que llegue la capa líquida
- **THEN** los tres botones funcionan y no hay indicador líquido

#### Scenario: Cambio de tema
- **WHEN** el usuario elige «Oscuro» con la capa líquida cargada
- **THEN** el tema cambia, el botón queda `aria-pressed` y el indicador se desplaza a esa opción

#### Scenario: Movimiento reducido
- **WHEN** el usuario prefiere movimiento reducido
- **THEN** no hay indicador líquido y el selector sigue cambiando el tema

### Requirement: Botones con anillo de metal en las acciones clave
«Añadir proyecto» (estado vacío de la portada y Ajustes) y «Reintentar review» SHALL ser un
`MetalButton`: con WebGL2 y sin movimiento reducido llevan un anillo de metal líquido (`metal-fx`) y,
en caso contrario, son exactamente el mismo botón sin anillo. Como el anillo sustituye el fondo del
botón, el botón SHALL usar siempre el aspecto neutro (color de texto normal, nunca el blanco sobre
verde de un botón primario), con o sin anillo, para que el texto cumpla el contraste AA y no haya
saltos al cargar. El botón SHALL seguir siendo un botón real, con foco visible y estado deshabilitado.

#### Scenario: Sin WebGL2
- **WHEN** el navegador no tiene WebGL2
- **THEN** «Añadir proyecto» es un botón neutro legible, sin anillo

#### Scenario: Con WebGL2
- **WHEN** hay WebGL2 y el usuario no pide movimiento reducido
- **THEN** el botón se muestra dentro del anillo de metal y responde a los clics

### Requirement: Héroe de los estados vacíos
La portada sin proyectos y el canal sin cambios SHALL mostrar como héroe una ilustración propia de la
marca (`HeroImage`). Con WebGL y sin movimiento reducido SHALL aparecer con el cargador «generando…»
de `img-fx` que se convierte en la imagen, en un solo pase, y quedarse en la imagen; en caso contrario,
o mientras llega la capa diferida, SHALL ser la misma imagen fija. La ilustración SHALL ser decorativa
(`alt` vacío). La capa de WebGL, y `three` con ella, NO SHALL formar parte del bundle principal. La
página «No encontrado» SHALL conservar su ilustración de líneas.

#### Scenario: Con WebGL
- **WHEN** se muestra un estado vacío en un navegador con WebGL
- **THEN** la imagen fija se ve mientras llega la capa y después se reproduce el efecto

#### Scenario: Sin WebGL o con movimiento reducido
- **WHEN** no hay WebGL o el usuario prefiere movimiento reducido
- **THEN** se muestra la imagen fija y no se descarga la capa de WebGL

#### Scenario: Peso del bundle
- **WHEN** se compila la aplicación
- **THEN** `border-beam`, `liquid-gooey`, `metal-fx` e `img-fx` (con `three`) van en chunks propios y
  el bundle principal no crece de forma apreciable

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

### Requirement: Avatares de agente con logo
La interfaz SHALL mostrar el logo de Claude y el de Codex como avatar de los agentes `claude` y
`codex` (sin distinguir mayúsculas) en todos los sitios donde se identifica a un agente. Cualquier
otro agente SHALL mostrar sus iniciales sobre un color estable. Si la imagen no carga, SHALL
mostrarse el avatar de iniciales. La imagen SHALL ser decorativa cuando el nombre del agente ya
aparece junto a ella.

#### Scenario: Agente con logo
- **WHEN** una review llega con el agente `Claude` o `codex`
- **THEN** su mensaje muestra la imagen del logo correspondiente como avatar

#### Scenario: Agente desconocido
- **WHEN** una review llega con el agente `agent_1`
- **THEN** su avatar muestra las iniciales «A1» y no un logo

#### Scenario: Imagen que no carga
- **WHEN** la imagen del logo falla al cargar
- **THEN** el avatar pasa a mostrar las iniciales del agente

### Requirement: Texto de las reviews con formato seguro
El resumen de una review y el mensaje de un hallazgo SHALL mostrarse con un formato mínimo:
párrafos, saltos de línea, código en línea, negrita, cursiva, listas, bloques de código y enlaces
http(s). La interfaz SHALL NOT interpretar HTML del texto, SHALL NOT crear enlaces que no sean
http o https y SHALL NOT mostrar imágenes del texto.

#### Scenario: Código en línea
- **WHEN** un resumen contiene `` `README.md` ``
- **THEN** se muestra «README.md» con estilo de código y sin los acentos graves

#### Scenario: HTML en el texto
- **WHEN** un hallazgo contiene `<script>alert(1)</script>` o `<img src=x onerror=alert(1)>`
- **THEN** el texto se muestra tal cual y no se crea ningún elemento `script` ni `img`

#### Scenario: Enlace no permitido
- **WHEN** el texto contiene `[pulsa](javascript:alert(1))`
- **THEN** no se crea ningún enlace y el texto se muestra como texto

### Requirement: Reviews legibles
Cada review SHALL presentarse con el nombre del agente, la etiqueta APP, el estado y los datos
(run, duración, nota) en la cabecera; después un bloque «Resumen» y, si hay hallazgos, un bloque
«Hallazgos» con su número. Cada hallazgo SHALL ser una tarjeta con la severidad coloreada y con
icono, la ubicación `archivo:línea` como chip que se puede copiar (omitido si no hay archivo), el
mensaje y, si el texto trae una etiqueta de recomendación (`Arreglo:`, `Sugerencia:`,
`Recomendación:`, `Fix:`, `Suggestion:`), la recomendación en un bloque aparte.

#### Scenario: Hallazgo con ubicación y recomendación
- **WHEN** un hallazgo trae archivo, línea y un texto con «Arreglo: …»
- **THEN** la tarjeta muestra el chip `archivo:línea`, el mensaje y la recomendación separada

#### Scenario: Hallazgo sin archivo
- **WHEN** un hallazgo no trae archivo
- **THEN** la tarjeta no muestra chip de ubicación

#### Scenario: Review fallida
- **WHEN** una review falló
- **THEN** se muestra el motivo saneado en una caja de error y ningún resumen

### Requirement: Filtro de hallazgos por severidad
El panel de hallazgos del detalle SHALL mostrar un contador por severidad y botones para filtrar
por una severidad, con estado accesible (`aria-pressed`). Sin filtro se muestran todos.

#### Scenario: Filtrar por severidad
- **WHEN** el usuario pulsa el botón de la severidad `bug`
- **THEN** el panel solo lista los hallazgos de severidad `bug` y el botón queda pulsado

### Requirement: Textos largos plegables
Un resumen o un hallazgo largo SHALL mostrarse plegado, con un botón «Ver más» (`aria-expanded`),
y SHALL poder desplegarse y volver a plegarse. El estado SHALL conservarse cuando la página se
refresca sola y cuando el componente se vuelve a montar.

#### Scenario: Plegado por defecto
- **WHEN** el resumen de una review supera el tamaño máximo
- **THEN** se muestra plegado con el botón «Ver más»

#### Scenario: Estado conservado
- **WHEN** el usuario despliega un resumen y la página se refresca sola
- **THEN** el resumen sigue desplegado

### Requirement: Review reutilizada visible
La interfaz SHALL mostrar en una review con `reused_from` una pill discreta «Reutilizada del commit
<sha corto>» (con `title` y texto accesible) y SHALL NOT mostrar el indicador «está revisando…» de
los agentes en un change cuyas reviews se reutilizaron.

#### Scenario: PR con reviews reutilizadas
- **WHEN** se abre el detalle de una PR con reviews reutilizadas
- **THEN** cada review muestra la pill con el SHA corto y no hay orbe de agentes pendientes

#### Scenario: Review propia
- **WHEN** una review no trae `reused_from`
- **THEN** no se muestra la pill

### Requirement: Logo de la aplicación según el tema
La interfaz SHALL mostrar como marca de la aplicación el logo de Duelo: la versión pensada para el
modo oscuro cuando el tema en vigor es oscuro y la pensada para el modo claro cuando es claro. El
logo SHALL cambiar al cambiar el tema (con el selector o con el esquema de color del sistema), SHALL
salir correcto desde la primera pintura y SHALL reservar su tamaño para no mover el diseño. La marca
de la barra superior SHALL acompañarse del texto «Duelo» y su imagen SHALL ser decorativa. El
logo SHALL ser la imagen principal de los estados vacíos y de la página de no encontrado.

#### Scenario: Tema oscuro
- **WHEN** el tema en vigor es oscuro
- **THEN** la barra superior muestra el logo de la versión oscura junto al texto «Duelo»

#### Scenario: Tema claro
- **WHEN** el tema en vigor es claro
- **THEN** la barra superior muestra el logo de la versión clara

#### Scenario: Cambio de tema
- **WHEN** el usuario cambia de Oscuro a Claro con el selector
- **THEN** el logo pasa a la versión clara sin recargar la página

#### Scenario: Estado vacío
- **WHEN** no hay proyectos vigilados
- **THEN** la imagen principal del estado vacío es el logo completo del tema en vigor

### Requirement: Icono de la pestaña según el esquema del sistema
La página SHALL declarar un icono de pestaña para cada esquema de color del sistema, claro y
oscuro, y un icono de Apple. SHALL NOT quedar referencia al icono anterior de las espadas.

#### Scenario: Iconos declarados
- **WHEN** se carga la página
- **THEN** el documento declara un icono para el esquema oscuro, otro para el claro y el icono de Apple

### Requirement: Commits deshechos y revertidos en el canal
La interfaz SHALL pintar la fila de un commit con `commit_state` `discarded` o `reverted` en ámbar
(fondo tintado y borde izquierdo ámbar con los tokens del tema, legible en oscuro y en claro), con un
icono de «deshacer» ámbar cuyo texto alternativo diga el estado, y SHALL mostrar en el centro de la
fila una etiqueta en mayúsculas («COMMIT DESHECHO» o «COMMIT REVERTIDO») con su subtítulo («Ya no
está en la rama» o «Revertido por `<sha corto>`»). El estado SHALL comunicarse también con texto y
no solo con el color. Las reviews, «Ver respuestas», los checks de los agentes y la vista compacta
SHALL seguir funcionando. Un commit deshecho o revertido SHALL contar como un cambio normal en los
contadores de revisión. La cabecera de la lista SHALL añadir los recuentos «N deshechos» y «N
revertidos» (de los cargados) cuando haya alguno.

#### Scenario: Commit deshecho
- **WHEN** un commit llega con `commit_state = discarded`
- **THEN** su fila es ámbar, muestra «COMMIT DESHECHO» y «Ya no está en la rama»

#### Scenario: Commit revertido
- **WHEN** un commit llega con `commit_state = reverted`
- **THEN** su fila muestra «COMMIT REVERTIDO» y «Revertido por <sha corto>»

#### Scenario: Vista compacta
- **WHEN** la densidad es compacta
- **THEN** la etiqueta se muestra en la misma línea y la fila sigue siendo ámbar

#### Scenario: Commit normal
- **WHEN** un commit es `active`
- **THEN** su fila no cambia

#### Scenario: Recuentos de la cabecera
- **WHEN** hay un commit deshecho y uno revertido entre los cargados
- **THEN** la cabecera de la lista dice «1 deshecho · 1 revertido» y los contadores de revisión no cambian

### Requirement: Aviso en el detalle de un commit deshecho o revertido
El detalle de un commit con `commit_state` `discarded` o `reverted` SHALL mostrar un aviso ámbar
destacado con el mismo texto que la fila y, si está revertido y se conoce el change del revert, un
enlace a él.

#### Scenario: Detalle de un commit revertido
- **WHEN** se abre el detalle de un commit revertido
- **THEN** aparece el aviso con «COMMIT REVERTIDO» y un enlace al change del revert

### Requirement: El logo se muestra completo
La interfaz SHALL mostrar el logo de la aplicación completo, sin partes recortadas por el borde de
su caja, en la barra superior y en los favicons, y SHALL reservar para el logo de la barra una caja
cuadrada de al menos 40 px para que la composición sea legible.

#### Scenario: Barra superior
- **WHEN** se muestra la barra superior en cualquier tema
- **THEN** el logo ocupa una caja cuadrada de 40 px y su contenido queda dentro de ella con margen, sin cortes

#### Scenario: Recortes con transparencia
- **WHEN** se usa un recorte del logo como marca
- **THEN** el recorte es un cuadrado con canal alfa, sin un fondo opaco propio
