## ADDED Requirements

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
