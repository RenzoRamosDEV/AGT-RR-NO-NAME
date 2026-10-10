## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Navegación por canales
La interfaz SHALL mostrar una barra lateral con un canal por proyecto y una sección General con
enlaces a Estadísticas y Ajustes, y SHALL marcar el destino activo con el color de énfasis.

#### Scenario: Abrir un canal
- **WHEN** el usuario selecciona un proyecto en la barra lateral
- **THEN** la ruta es `/p/:slug` y el canal aparece marcado como activo

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

## REMOVED Requirements

### Requirement: Tema negro único
**Reason**: el tema negro puro con acento blanco no daba jerarquía visual y se sustituye por la
estética de GitHub y Slack con tema claro y oscuro (ADR 0003).
**Migration**: los requisitos «Temas claro y oscuro», «Marco de la aplicación» y «Contraste
accesible» describen el comportamiento nuevo; el ADR 0002 queda sustituido por el 0003.
