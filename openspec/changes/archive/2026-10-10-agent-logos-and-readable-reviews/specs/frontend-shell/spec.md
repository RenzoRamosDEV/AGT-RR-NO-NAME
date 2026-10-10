## ADDED Requirements

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
