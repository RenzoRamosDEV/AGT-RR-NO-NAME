# change-queries Specification

## Purpose
TBD - created by archiving change round1-backend-api. Update Purpose after archive.

## Requirements

### Requirement: Listado de proyectos
El sistema SHALL exponer `GET /projects`, que devuelve todos los proyectos vigilados con su
`id`, `slug`, `path` (la carpeta local, o `null` si el proyecto no se dio de alta desde una),
`hooks_installed` y `github`, ordenados por slug.

#### Scenario: Varios proyectos
- **WHEN** existen los proyectos `b/repo` y `a/repo`
- **THEN** la respuesta es 200 y los lista en el orden `a/repo`, `b/repo`

#### Scenario: Sin proyectos
- **WHEN** no existe ningún proyecto
- **THEN** la respuesta es 200 con una lista vacía

#### Scenario: Proyecto local y proyecto sin carpeta
- **WHEN** existe un proyecto dado de alta desde `/home/u/repo` y otro creado sin carpeta
- **THEN** el primero lleva `path` `/home/u/repo` con `hooks_installed` verdadero, y el segundo lleva
  `path` `null`, `hooks_installed` falso y `github` falso

### Requirement: Canal paginado de un proyecto
El sistema SHALL exponer `GET /projects/{slug}/changes`, que devuelve los changes del
proyecto del más reciente al más antiguo, sin su diff, filtrables por `kind` y paginados
con `limit` (1 a 100, 50 por defecto) y un cursor opaco: la respuesta incluye `next_cursor`
solo si quedan más changes, y pasarlo como `cursor` devuelve la página siguiente sin repetir
ni saltarse ninguno, aunque varios changes compartan instante de creación.

#### Scenario: Orden y filtro por tipo
- **WHEN** un proyecto tiene commits y PRs y se pide `kind=pr`
- **THEN** solo se devuelven los PRs, del más reciente al más antiguo

#### Scenario: Paginación completa
- **WHEN** un proyecto tiene cinco changes y se pide `limit=2` encadenando `next_cursor`
- **THEN** se obtienen páginas de 2, 2 y 1 elementos, sin repetidos ni omitidos, y la última
  página no incluye `next_cursor`

#### Scenario: Proyecto desconocido
- **WHEN** se pide el canal de un proyecto que no existe
- **THEN** la respuesta es 404

#### Scenario: Cursor inválido o límite fuera de rango
- **WHEN** se envía un `cursor` que no es uno devuelto por el sistema, o un `limit` fuera de
  1 a 100
- **THEN** la respuesta es 422 y no se consulta la base de datos

### Requirement: Detalle de un change
El sistema SHALL exponer `GET /changes/{id}`, que devuelve el change con su diff y todas sus
reviews (completadas y fallidas) ordenadas por fecha, sin incluir la salida cruda del agente.

#### Scenario: Change con reviews completada y fallida
- **WHEN** un change tiene una review completada y otra fallida
- **THEN** la respuesta es 200 con el change, su diff y ambas reviews; la fallida lleva su
  `error` y la completada su `summary`, `score` y `findings`

#### Scenario: Change inexistente
- **WHEN** se pide un id que no corresponde a ningún change
- **THEN** la respuesta es 404

### Requirement: Métricas agregadas por agente
El sistema SHALL exponer `GET /stats/agents`, que devuelve por cada agente con reviews el
total, las completadas, las fallidas, la duración media y el score medio, ignorando los
valores nulos en las medias (media nula si no hay ningún valor). Con el parámetro opcional
`project=owner/repo` SHALL limitar las métricas a las reviews de los changes de ese proyecto;
sin él, el agregado es global. Un `project` desconocido SHALL responder 404, y uno con NUL o de
más de 255 caracteres, 422.

#### Scenario: Agente con reviews completadas y fallidas
- **WHEN** un agente tiene dos reviews completadas (score 8 y 6, 100 ms y 300 ms) y una fallida
  sin score
- **THEN** sus métricas son total 3, completadas 2, fallidas 1, score medio 7 y duración
  media 200 ms

#### Scenario: Agente solo con fallos
- **WHEN** un agente solo tiene reviews fallidas sin score
- **THEN** su score medio es nulo

#### Scenario: Sin reviews
- **WHEN** no hay ninguna review
- **THEN** la respuesta es 200 con una lista vacía

#### Scenario: Filtrado por proyecto
- **WHEN** existen reviews de un agente en los proyectos `a/repo` y `b/repo` y se pide
  `?project=a/repo`
- **THEN** las métricas solo cuentan las reviews de los changes de `a/repo`

#### Scenario: Proyecto sin reviews
- **WHEN** `project` existe pero sus changes no tienen reviews
- **THEN** la respuesta es 200 con una lista vacía

#### Scenario: Proyecto desconocido
- **WHEN** `project` no corresponde a ningún proyecto
- **THEN** la respuesta es 404

### Requirement: Filtros del canal por estado de review y texto
El sistema SHALL aceptar en `GET /projects/{slug}/changes` el parámetro `status` (repetible,
con los valores `pending`, `running`, `partial_failed`, `failed` y `completed`) y el parámetro
`q`, y devolver solo los changes cuyo `review_status` esté entre los indicados y cuyo título,
autor, SHA o ref contengan `q` sin distinguir mayúsculas. Los filtros SHALL combinarse entre sí
y con `kind`, y SHALL respetar la paginación por cursor. Los caracteres `%`, `_` y `\` de `q`
SHALL tratarse como texto literal. Un `q` vacío tras recortarlo SHALL ignorarse; un `q` con NUL o de
más de 100 caracteres, o un `status` desconocido, SHALL responder 422.

#### Scenario: Filtro por estado
- **WHEN** el canal tiene changes `completed` y `failed` y se pide `status=failed`
- **THEN** solo se devuelven los `failed`

#### Scenario: Varios estados
- **WHEN** se pide `status=pending&status=running`
- **THEN** se devuelven los changes en cualquiera de los dos estados

#### Scenario: Búsqueda por texto
- **WHEN** se pide `q=ReNzO` y solo un change tiene ese autor, en cualquier capitalización
- **THEN** solo se devuelve ese change; lo mismo ocurre al buscar un fragmento del título, del
  SHA o del ref

#### Scenario: Comodines literales
- **WHEN** se pide `q=50%` y un change tiene "50% más rápido" en el título y otro "500 casos"
- **THEN** solo se devuelve el primero

#### Scenario: Filtros con paginación
- **WHEN** hay cinco changes que cumplen `status=failed` y se pide `limit=2` encadenando `next_cursor`
- **THEN** se recorren los cinco, sin repetir ni omitir, y ninguno de otro estado

#### Scenario: Parámetros inválidos
- **WHEN** se envía `status=desconocido` o un `q` con NUL
- **THEN** la respuesta es 422

### Requirement: Estado agregado de las reviews de un change
El sistema SHALL incluir en cada change del canal y en su detalle el campo `review_status`,
calculado sobre las reviews del `run` actual del change frente al número de agentes configurados:
`pending` si no hay ninguna; `running` si hay menos que agentes; y, con todas registradas,
`completed` si ninguna falló, `failed` si todas fallaron y `partial_failed` en otro caso. Las
reviews de runs anteriores NO SHALL contar.

#### Scenario: Sin reviews
- **WHEN** un change recién ingerido no tiene reviews
- **THEN** su `review_status` es `pending`

#### Scenario: Faltan agentes
- **WHEN** hay dos agentes configurados y solo uno ha registrado su review, completada o fallida
- **THEN** el `review_status` es `running`

#### Scenario: Todas registradas
- **WHEN** ambos agentes han registrado su review
- **THEN** es `completed` si ninguna falló, `failed` si fallaron las dos y `partial_failed` si
  falló una

#### Scenario: Un reintento reinicia el estado
- **WHEN** el change avanza a `run = 2` y aún no hay reviews de ese run
- **THEN** su `review_status` es `pending`, aunque el run 1 tuviera reviews

### Requirement: Resumen de findings de un change
El sistema SHALL incluir en el detalle de un change `findings_summary` con `total` y
`by_severity` (`bug`, `risk`, `improvement`, `nit`, `other`), contando los findings de las
reviews completadas del `run` actual. Las severidades SHALL normalizarse (sin distinguir
mayúsculas ni espacios, con sinónimos conocidos) y las desconocidas contarse como `other`. La
respuesta NO SHALL incluir la salida cruda del agente.

#### Scenario: Findings de varias reviews
- **WHEN** dos reviews del run actual aportan tres findings `bug`, `Risk` y `nit`
- **THEN** `total` es 3 y `by_severity` cuenta uno en `bug`, uno en `risk` y uno en `nit`

#### Scenario: Severidad desconocida
- **WHEN** un finding tiene severidad `"banana"`
- **THEN** cuenta en `other` y el `total` lo incluye

#### Scenario: Sin findings
- **WHEN** el change no tiene reviews completadas con findings
- **THEN** `total` es 0 y todos los contadores son 0

#### Scenario: Runs anteriores
- **WHEN** el change está en `run = 2` y las reviews del run 1 tenían findings
- **THEN** esos findings no cuentan

### Requirement: Resumen del diff de un change
El sistema SHALL incluir en cada change, tanto en `GET /projects/{slug}/changes` como en
`GET /changes/{id}`, un `diff_summary` con `files_changed` (recuento real de archivos),
`additions`, `deletions` y `files` (hasta 200 entradas con `path`, `additions` y `deletions`).
El resumen se calcula al ingerir el change, se guarda con él y el listado SHALL obtenerlo sin
cargar el diff. Las cabeceras `---`/`+++` no cuentan como líneas, y una línea de contenido que
empiece por `++` o `--` dentro de un hunk sí. Los changes anteriores a esta capacidad SHALL
quedar rellenados por la migración.

#### Scenario: Diff con dos archivos
- **WHEN** se ingiere un diff que añade 3 líneas y borra 1 en `a.py` y añade 2 en `b.py`
- **THEN** `diff_summary` es `files_changed = 2`, `additions = 5`, `deletions = 1` y `files`
  lista `a.py` (3/1) y `b.py` (2/0)

#### Scenario: Contenido que empieza por guiones
- **WHEN** un hunk borra una línea que contiene `-- comentario` y añade otra que contiene `++x`
- **THEN** ambas cuentan como borrada y añadida respectivamente

#### Scenario: Diff vacío o sin formato git
- **WHEN** el diff está vacío o no contiene `diff --git`
- **THEN** `diff_summary` tiene `files_changed = 0` y `files` vacío

#### Scenario: Lista de archivos acotada
- **WHEN** el diff toca más de 200 archivos
- **THEN** `files_changed` es el recuento real y `files` contiene solo los primeros 200

#### Scenario: Change anterior a la migración
- **WHEN** existía un change con diff antes de aplicar la migración
- **THEN** tras migrar su `diff_summary` coincide con el que calcularía la ingesta

### Requirement: Reviews ligeras en el canal
Cada elemento de `GET /projects/{slug}/changes` SHALL incluir `reviews`: la lista de las reviews del
`run` actual del change, ordenadas por agente, con únicamente `agent`, `status`, `score`,
`duration_ms` y `run`. Esa lista NUNCA SHALL incluir resumen, hallazgos, error, salida cruda ni el
diff, que se obtienen con `GET /changes/{id}`. Las reviews de runs anteriores SHALL NO aparecer. El
sistema SHALL obtener las de toda la página con una única consulta adicional (sin una consulta por
change) y el campo SHALL ser aditivo: el resto del contrato del listado no cambia.

#### Scenario: Un change con reviews
- **WHEN** un change con una review completada y otra fallida en su run actual aparece en el canal
- **THEN** su `reviews` trae las dos con `agent`, `status`, `score`, `duration_ms` y `run`, y ningún
  texto de resumen, hallazgo, error ni salida cruda

#### Scenario: Tras un reintento
- **WHEN** un change tiene una review fallida en el run 1 y una completada en el run 2 (el actual)
- **THEN** su `reviews` solo contiene la del run 2

#### Scenario: Un change sin reviews
- **WHEN** un change aún no tiene reviews
- **THEN** su `reviews` es una lista vacía

#### Scenario: Sin consulta por change
- **WHEN** el canal devuelve una página de varios changes
- **THEN** las reviews ligeras de toda la página salen de una sola consulta adicional a la base de
  datos, que no lee las columnas de resumen, hallazgos, error ni salida cruda
