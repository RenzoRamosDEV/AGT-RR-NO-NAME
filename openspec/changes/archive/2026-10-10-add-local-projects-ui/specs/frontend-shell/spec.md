## ADDED Requirements

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
