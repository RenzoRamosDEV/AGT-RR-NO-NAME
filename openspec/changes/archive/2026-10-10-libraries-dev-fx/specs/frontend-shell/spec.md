## ADDED Requirements

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
