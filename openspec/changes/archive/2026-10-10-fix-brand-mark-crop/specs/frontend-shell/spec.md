## ADDED Requirements

### Requirement: El logo se muestra completo
La interfaz SHALL mostrar el logo de la aplicación completo, sin partes recortadas por el borde de
su caja, en la barra superior y en los favicons, y SHALL reservar para el logo de la barra una caja
cuadrada de al menos 40 px para que la composición sea legible.

#### Scenario: Barra superior
- **WHEN** se muestra la barra superior en cualquier tema
- **THEN** el logo ocupa una caja cuadrada de 40 px y su contenido queda dentro de ella con margen, sin cortes

#### Scenario: Recortes con transparencia
- **WHEN** se usa un recorte del logo como marca
- **THEN** el recorte es un cuadrado con canal alfa, sin un fondo opaco propio
