## ADDED Requirements

### Requirement: Navegador de archivos del diff
El detalle de un change SHALL mostrar, si el diff tiene archivos identificables, una lista de los
archivos tocados con sus líneas añadidas y borradas y enlaces que saltan a la sección de cada
archivo. SHALL reconocer cabeceras `@@ <archivo>` y `diff --git`, y no SHALL contar las líneas de
metadatos (`index`, `---`, `+++`) como cambios.

#### Scenario: Dos archivos
- **WHEN** el diff toca `a.py` (+2 −1) y `b.py` (+1 −0)
- **THEN** la lista muestra ambos archivos con «+2 −1» y «+1 −0» y cada uno enlaza a su sección

#### Scenario: Diff estilo git
- **WHEN** el diff contiene `--- a/x`, `+++ b/x` y un hunk con una línea añadida
- **THEN** el recuento del archivo es +1 −0

### Requirement: Ordenación de estadísticas
La tabla de estadísticas SHALL poder ordenarse por cada columna mediante botones en las
cabeceras, SHALL indicar la columna y el sentido activos con `aria-sort` y SHALL invertir el
sentido al volver a pulsar la misma columna.

#### Scenario: Ordenar por fallos
- **WHEN** el usuario pulsa la cabecera «Fallos»
- **THEN** las filas quedan ordenadas por fallos ascendente y la cabecera indica `aria-sort="ascending"`

#### Scenario: Invertir el sentido
- **WHEN** el usuario pulsa «Fallos» dos veces
- **THEN** el orden es descendente y `aria-sort="descending"`

### Requirement: Antigüedad de los changes
Cada change del canal SHALL mostrar su antigüedad relativa («hace 12 min») en un elemento `<time>`
con la fecha absoluta en `datetime` y `title`. Si el change no tiene fecha SHALL omitirla.

#### Scenario: Cambio reciente
- **WHEN** un change se creó hace 12 minutos
- **THEN** se muestra «hace 12 min» y el `datetime` contiene la fecha ISO original

### Requirement: Vista compacta del canal
El canal SHALL ofrecer un interruptor entre tarjetas y filas compactas, conservando búsqueda,
filtros y la posibilidad de ver las respuestas de cada change.

#### Scenario: Cambiar a compacta
- **WHEN** el usuario pulsa «Compacta»
- **THEN** los changes se listan en filas, el botón queda con `aria-pressed="true"` y los filtros se mantienen

### Requirement: Estado vacío accionable
Un canal sin changes y sin filtros activos SHALL mostrar el comando mínimo para ingestar un commit
del proyecto, usando un token de ejemplo y nunca uno real, con un botón para copiarlo.

#### Scenario: Proyecto sin changes
- **WHEN** se abre un proyecto sin changes
- **THEN** se muestra un comando que incluye el slug del proyecto y `$INGEST_TOKEN`
