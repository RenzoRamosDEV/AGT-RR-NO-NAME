# workflow-observability Specification

## Purpose
TBD - created by archiving change temporal-readable-workflows. Update Purpose after archive.

## Requirements

### Requirement: Nombres legibles de los workflows
El workflow padre de una review SHALL llamarse `{kind}-{repo}-{sha12}-{proyecto6}` y, desde el
segundo `run`, `…-r{run}`; su hijo SHALL llamarse `review-{kind}-{repo}-{sha12}-{proyecto6}-r{run}`. `kind` es
`commit` o `pr`; `repo` es el nombre `owner/repo` del proyecto en minúsculas, solo con `[a-z0-9._-]`
(el resto, incluida la barra, pasa a `-`), sin guiones repetidos ni en los extremos y de 60
caracteres como máximo; `sha12` son los 12 primeros caracteres alfanuméricos del SHA y `proyecto6` los
6 primeros hex del UUID del proyecto. El id SHALL ser el mismo para el mismo proyecto, tipo, SHA y `run`
y distinto si cambia cualquiera de ellos.

#### Scenario: Un commit
- **WHEN** se arranca la review de un commit del proyecto `acme/widgets`
- **THEN** el workflow se llama `commit-acme-widgets-<sha12>-<proyecto6>` y su hijo
  `review-commit-acme-widgets-<sha12>-<proyecto6>-r1`

#### Scenario: Una PR y un reintento
- **WHEN** se arranca la review de una PR y después su reintento
- **THEN** los ids empiezan por `pr-` y el del reintento termina en `-r2`

#### Scenario: Un commit y una PR con el mismo SHA
- **WHEN** un commit y una PR del mismo proyecto comparten el SHA
- **THEN** sus workflows y sus hijos tienen ids distintos y se hacen las dos reviews

#### Scenario: Proyecto quitado y vuelto a añadir
- **WHEN** se quita un proyecto, se vuelve a añadir con el mismo nombre y se reenvía el mismo commit
- **THEN** el id es distinto (otro `proyecto6`) y Temporal arranca la review en lugar de ignorarla

### Requirement: La respuesta de cada reviewer se lee en el historial de Temporal
El resultado de la activity `run_review` SHALL incluir el agente, el estado, el resumen, la nota, los
hallazgos (`severity`, `file`, `line`, `message`), el total real de hallazgos, el error de una review
fallida y la duración, de forma acotada: resumen de hasta 2000 caracteres, hasta 30 hallazgos, mensajes
y ficheros de hasta 300, error de hasta 300 sin credenciales. SHALL indicar con `truncated` si se cortó
algo y NUNCA incluir el diff ni la salida cruda de un CLI.

#### Scenario: Review completada
- **WHEN** un agente completa su review
- **THEN** el evento `ActivityTaskCompleted` y el resultado del hijo y del padre llevan su resumen,
  nota y hallazgos

#### Scenario: Texto demasiado largo
- **WHEN** el resumen supera 2000 caracteres o hay más de 30 hallazgos
- **THEN** el resultado se recorta, `truncated` es `true` y `findings_total` conserva el total real

#### Scenario: Review fallida con una credencial en el error
- **WHEN** una review falla con el mensaje `sin sesión token=abc`
- **THEN** el resultado lleva `sin sesión token=[oculto]`

#### Scenario: Histórico anterior
- **WHEN** Temporal deserializa un resultado que solo tenía `status` y `review_id`
- **THEN** los campos nuevos toman su valor por defecto y no hay error

### Requirement: Resúmenes y detalles de usuario
Cada workflow SHALL llevar un resumen estático («commit · repo · título») y una ficha en markdown; cada
actividad `run_review` un resumen de una línea («claude revisa 3f2a9c1»); y el workflow hijo SHALL
publicar «Current Details» con una línea por agente (nombre, estado, nota, hallazgos por severidad y un
extracto del resumen), actualizada según terminan. Todo texto escrito por un agente o un autor SHALL
escaparse para que no tenga efecto en el markdown ni inyecte HTML.

#### Scenario: Detalles mientras trabajan los agentes
- **WHEN** un agente ha terminado y otro sigue revisando
- **THEN** los detalles muestran «completada» para el primero y «revisando…» para el segundo

#### Scenario: Texto hostil
- **WHEN** el resumen de un agente contiene `**negrita**` o `<img onerror=…>`
- **THEN** los detalles lo muestran como texto y no como formato ni etiqueta

### Requirement: Compatibilidad con ejecuciones y servidores anteriores
Una ejecución que no lleve los datos de presentación en su entrada (anterior a este cambio) SHALL
conservar el id antiguo de su hijo (`review-{change_id}-r{run}`) y su historia SHALL reproducirse sin
errores de no determinismo; los cambios de comportamiento van bajo
`workflow.patched("readable-workflow-names")`. Los campos nuevos de los DTO SHALL tener valor por
defecto, de modo que un worker antiguo ignore los campos de más y uno nuevo lea históricos antiguos.

#### Scenario: Replay de una historia anterior
- **WHEN** se reproduce con el workflow nuevo la historia de una ejecución grabada antes de este cambio
- **THEN** no hay error de no determinismo

#### Scenario: Entrada antigua
- **WHEN** se arranca el padre con una entrada sin repo, SHA ni proyecto
- **THEN** el hijo se llama `review-{change_id}-r{run}` y no lleva resumen estático

### Requirement: No relanzar a los agentes por el cambio de id
Antes de arrancar un workflow con el id nuevo, el starter SHALL consultar el id antiguo
(`{kind}-{proyecto}-{sha}[-r{run}]`): si esa ejecución existe y está en marcha o terminó bien, NO SHALL
arrancar otra; si falló, se canceló, se terminó a mano o agotó su plazo, SHALL arrancar con el id nuevo.

#### Scenario: Commit ya revisado con el id antiguo
- **WHEN** se reenvía un commit cuya review terminó con el id antiguo
- **THEN** no se arranca ningún workflow nuevo

#### Scenario: Ejecución antigua fallida
- **WHEN** se reenvía un commit cuya ejecución con el id antiguo falló
- **THEN** se arranca la review con el id nuevo

#### Scenario: Solo el run 2 tenía id antiguo
- **WHEN** solo el `run` 2 arrancó con el id antiguo y se reenvían ambos `run`
- **THEN** el `run` 2 no se vuelve a arrancar y el `run` 1 sí

### Requirement: Versiones de Temporal que muestran los metadatos
El `docker-compose.yml` SHALL usar un servidor y una interfaz de Temporal que guarden y muestren los
resúmenes y detalles de usuario.

#### Scenario: Servidor de desarrollo
- **WHEN** se levanta la infraestructura con `just dev`
- **THEN** el servidor es `auto-setup:1.26.2` y la interfaz `ui:2.36.1`

### Requirement: Sin credenciales en el historial de Temporal
Todo texto libre que Duelo copie al historial de Temporal SHALL salir sin credenciales y SHALL
redactarse antes de acotarse a su longitud máxima. Alcanza al resumen, el fichero, el mensaje y la
severidad de cada hallazgo, al error de una review fallida, al título del change (en la entrada del
workflow y en los resúmenes y fichas estáticos) y a los «Current Details». Se ocultan los pares
`token`, `secret`, `password`, `passwd`, `api_key` y `authorization` con su valor (incluido el esquema
`Bearer` o `Basic`), `Bearer …`, `sk-…`, los tokens de GitHub, las claves de acceso de AWS, los tokens
de Slack, los JWT y las claves privadas PEM. La tabla `reviews` y la API de lectura NO cambian.

#### Scenario: Credencial citada en una review completada
- **WHEN** un agente completa su review con el resumen «El diff incluye token=abc123 y la clave sk-abcdefghijklmnop1234»
- **THEN** el resultado de la activity lleva «El diff incluye token=[oculto] y la clave [oculto]» y
  ningún evento del historial contiene `abc123` ni la clave

#### Scenario: Credencial en un hallazgo
- **WHEN** un hallazgo dice «password = hunter2 escrito en el código» sobre un fichero `sk-abcdefghijklmnop1234.env`
- **THEN** su mensaje y su fichero salen con el valor oculto

#### Scenario: Credencial en el título del commit
- **WHEN** el título del change es «fix: usar token=abc123»
- **THEN** la entrada del workflow, su resumen estático y su ficha llevan `token=[oculto]`

#### Scenario: Cabecera Authorization
- **WHEN** un texto contiene `Authorization: Bearer eyJhbGci.payload`
- **THEN** se oculta el token y no solo la palabra «Bearer»

#### Scenario: Se redacta antes de cortar
- **WHEN** una credencial queda partida por el límite de longitud
- **THEN** no queda ningún fragmento de ella a la vista

#### Scenario: Redactar no es truncar
- **WHEN** un texto solo cambia por la redacción
- **THEN** `truncated` sigue siendo `false`
