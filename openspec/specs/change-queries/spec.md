# change-queries Specification

## Purpose
TBD - created by archiving change round1-backend-api. Update Purpose after archive.

## Requirements

### Requirement: Listado de proyectos
El sistema SHALL exponer `GET /projects`, que devuelve todos los proyectos vigilados con su
`id` y `slug`, ordenados por slug.

#### Scenario: Varios proyectos
- **WHEN** existen los proyectos `b/repo` y `a/repo`
- **THEN** la respuesta es 200 y los lista en el orden `a/repo`, `b/repo`

#### Scenario: Sin proyectos
- **WHEN** no existe ningún proyecto
- **THEN** la respuesta es 200 con una lista vacía

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
valores nulos en las medias (media nula si no hay ningún valor).

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
