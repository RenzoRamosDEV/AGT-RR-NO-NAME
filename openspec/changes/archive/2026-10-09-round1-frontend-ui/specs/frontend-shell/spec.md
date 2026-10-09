## ADDED Requirements

### Requirement: Navegación adaptable
En pantallas estrechas la barra lateral SHALL ocultar sus enlaces tras un botón "Menú" que
exponga su estado con `aria-expanded`, SHALL cerrarse al navegar o al pulsar Escape, y SHALL
mantener los enlaces operables con teclado.

#### Scenario: Abrir y cerrar el menú
- **WHEN** el usuario activa el botón "Menú"
- **THEN** `aria-expanded` pasa a `true` y, al pulsar Escape, vuelve a `false`

#### Scenario: Navegar con el menú abierto
- **WHEN** el menú está abierto y el usuario sigue un enlace
- **THEN** la ruta cambia y el menú queda cerrado

### Requirement: Búsqueda en el canal
El canal SHALL ofrecer un campo de búsqueda que filtre los changes por título, autor o SHA sin
distinguir mayúsculas, combinado con el filtro por tipo, y SHALL indicar cuando no hay
coincidencias.

#### Scenario: Buscar por SHA
- **WHEN** el usuario escribe parte del SHA de un change
- **THEN** solo se listan los changes cuyo SHA contiene ese texto

#### Scenario: Sin coincidencias
- **WHEN** ningún change cumple la búsqueda y el filtro
- **THEN** se muestra "Ningún cambio coincide con la búsqueda."

### Requirement: Resumen de reviews por change
Cada change del canal SHALL mostrar, sin desplegar el hilo, cuántas reviews están completadas,
en curso o fallidas, con texto además de color.

#### Scenario: Change con reviews mixtas
- **WHEN** un change tiene una review completada y otra en curso
- **THEN** su card muestra "1 completada" y "1 en curso"

### Requirement: Diff legible
El detalle de un change SHALL mostrar el diff con líneas numeradas, la cabecera de archivo
diferenciada y las líneas añadidas o borradas distinguibles sin depender solo del color, y SHALL
avisar cuando el diff está truncado.

#### Scenario: Diff con añadidos y borrados
- **WHEN** se abre un change con líneas `+` y `-`
- **THEN** cada línea muestra su número y las añadidas y borradas llevan una marca textual

#### Scenario: Diff truncado
- **WHEN** el change tiene el diff truncado
- **THEN** se muestra un aviso de que solo se ve una parte del diff

### Requirement: Estadísticas con barras compactas
La página de estadísticas SHALL acompañar `% útiles`, duración y fallos con una barra
proporcional decorativa, manteniendo el valor numérico en la tabla.

#### Scenario: Valor accesible
- **WHEN** un lector de pantalla recorre la tabla
- **THEN** lee el valor numérico de cada celda y las barras no se anuncian
