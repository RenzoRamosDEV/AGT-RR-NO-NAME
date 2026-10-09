## ADDED Requirements

### Requirement: Navegación con slugs owner/repo
La interfaz SHALL servir el canal de un proyecto en `/p/<slug>` y el detalle de un change en
`/p/<slug>/changes/<id>`, donde `<slug>` puede tener varios segmentos (`owner/repo`). Todos los
enlaces internos a un proyecto o a un change SHALL construirse con un único helper que codifique
cada segmento.

#### Scenario: Canal de un proyecto con barra
- **WHEN** el usuario abre `/p/acme/widgets`
- **THEN** se muestra el canal de `acme/widgets`

#### Scenario: Detalle de un change de un proyecto con barra
- **WHEN** el usuario abre `/p/acme/widgets/changes/c1`
- **THEN** se muestra el detalle del change `c1`, con una miga que enlaza a `/p/acme/widgets`

#### Scenario: Entrada por la raíz
- **WHEN** el usuario abre `/` y el primer proyecto es `acme/widgets`
- **THEN** la interfaz redirige a `/p/acme/widgets` y muestra su canal

#### Scenario: Slug de un solo segmento
- **WHEN** el usuario abre `/p/duelo`
- **THEN** se muestra el canal de `duelo`

### Requirement: Página no encontrado
Una URL que no corresponda a ninguna página SHALL mostrar un mensaje «No encontrado» con un
enlace al inicio, dentro de la estructura habitual, y SHALL NOT dejar la página en blanco.

#### Scenario: Ruta desconocida
- **WHEN** el usuario abre `/nada`
- **THEN** se muestra «No encontrado» y un enlace al inicio

#### Scenario: Proyecto sin slug
- **WHEN** el usuario abre `/p`
- **THEN** se muestra «No encontrado»
