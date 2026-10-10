## MODIFIED Requirements

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
