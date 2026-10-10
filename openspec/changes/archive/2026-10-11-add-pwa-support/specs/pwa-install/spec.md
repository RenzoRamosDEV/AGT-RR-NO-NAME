## ADDED Requirements

### Requirement: Aplicación instalable
La aplicación SHALL publicar un manifiesto web con nombre, nombre corto, idioma, `start_url`,
`display: standalone`, colores de tema y fondo, e iconos de 192 y 512 píxeles más uno
`maskable`, de modo que el navegador ofrezca instalarla.

#### Scenario: Manifiesto válido
- **WHEN** se carga la aplicación servida por HTTPS o `localhost` desde el build de producción
- **THEN** el navegador detecta el manifiesto con sus iconos y la aplicación cumple los criterios
  de instalación

#### Scenario: Icono con zona segura
- **WHEN** el sistema recorta el icono `maskable` con una máscara circular o redondeada
- **THEN** el emblema de Duelo queda completo dentro de la zona segura

### Requirement: Interfaz disponible sin conexión
El build de producción SHALL precachear el *app shell* mediante un service worker, de modo que la
aplicación abra y navegue entre sus rutas sin red tras la primera visita.

#### Scenario: Abrir sin red
- **WHEN** el usuario abre la aplicación ya visitada sin conexión
- **THEN** se muestra la interfaz y, donde faltan datos, sus estados de error habituales

#### Scenario: Ruta de la SPA sin red
- **WHEN** el usuario recarga `/stats` sin conexión
- **THEN** se sirve la interfaz y la ruta se resuelve en el cliente

### Requirement: Los datos no se cachean
El service worker SHALL NOT interceptar ni cachear las peticiones a la API, ni las de otros
orígenes; siempre SHALL ir a la red.

#### Scenario: Sin datos obsoletos
- **WHEN** la API deja de responder o no hay conexión
- **THEN** la interfaz muestra un error de carga y no reviews guardadas de una visita anterior

### Requirement: Actualización controlada
Cuando haya una versión nueva, la aplicación SHALL avisar con un mensaje operable con teclado y un
botón para recargar, y SHALL NOT recargar la página por su cuenta.

#### Scenario: Nueva versión disponible
- **WHEN** el service worker detecta una versión nueva
- **THEN** aparece el aviso «Nueva versión disponible» con el botón «Actualizar» y, al
  pulsarlo, la aplicación se recarga con la versión nueva

### Requirement: Sin service worker en desarrollo
El service worker SHALL registrarse solo en el build de producción.

#### Scenario: Servidor de desarrollo
- **WHEN** se ejecuta `vite` en desarrollo
- **THEN** no se registra ningún service worker y los cambios de código se ven al instante
