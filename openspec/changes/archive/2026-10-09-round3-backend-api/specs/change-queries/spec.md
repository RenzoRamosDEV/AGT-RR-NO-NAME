# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

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
