# Proposal

## Por qué

Al auditar la suite contra el checklist de tipos de test (valores límite, casos negativos,
particiones de equivalencia) se sondeó la persistencia real con entradas en los bordes. El
sondeo, contra Postgres real, encontró **defectos reales** que ningún test cubría:

- Cualquier campo por encima del límite de su columna revienta con un error de base de
  datos: `head_sha` > 64, `ref` > 255, `url` > 1000, `title` > 500, `author` > 255 (y
  `agent` > 50 en las reviews). Cuando exista la API serían respuestas 500 opacas.
- Cualquier carácter NUL (`\x00`) en texto, en el diff o en el contenido de una review
  (incluido el JSONB de `findings`) revienta igual: Postgres no puede almacenarlo.

Sí funcionan bien (y quedarán fijados como tests de regresión): diff de 5 MB, comillas e
intentos de inyección SQL guardados como texto literal, y Unicode/emoji.

## Qué cambia

- **Identificadores acotados y validados en el dominio.** `Change.new` rechaza con
  `ValueError` un `head_sha` vacío, > 64 o con NUL, y un `ref` > 255 o `url` > 1000 (o con
  NUL), antes de tocar la base de datos. Son identificadores o enlaces: recortarlos los
  corrompería.
- **Metadatos de visualización recortados.** `title` (500) y `author` (255) se recortan en
  vez de rechazar el commit: perder una review por un asunto demasiado largo es peor que
  guardarlo truncado.
- **NUL saneado en los adaptadores de persistencia.** Es una limitación de Postgres, no una
  regla de negocio, así que vive en `adapters/persistence/`: el NUL se sustituye por
  `U+FFFD` en `title`, `author` y `diff` de los changes, y en `summary`, `raw_output`,
  `error` y en los textos de `findings` de las reviews.
- **Nombre de agente acotado.** `Review.succeeded`/`Review.failed` rechazan un nombre de
  agente vacío o de más de 50 caracteres.
- **Guarda contra deriva dominio ↔ esquema**: un test compara las constantes de límite del
  dominio con las longitudes reales de las columnas del modelo SQLAlchemy.

Fuera de este change: la reorganización general de la suite y el resto de tipos de test
(`strengthen-test-suite`), y el mapeo de estos rechazos a códigos HTTP (llega con la API).

## Capacidades

### Nuevas capacidades

(ninguna)

### Capacidades modificadas

- `change-ingestion`: identificadores acotados y validados, metadatos de visualización
  recortados y contenido con NUL aceptado.
- `change-review`: nombre de agente acotado y contenido de review con NUL aceptado.

## Impacto

- `backend/src/review_arena/domain/` (`change.py`, `review.py`),
  `backend/src/review_arena/adapters/persistence/` (nuevo `sanitize.py`, repositorios).
- Dependencia nueva de desarrollo: `hypothesis` (property-based testing del saneado y
  del recorte, donde aporta valor real: la propiedad "ninguna cadena produce NUL ni excede
  el límite" no se cubre bien con ejemplos).
- Sin migración de esquema (los límites ya son los de las columnas actuales).
- Done-when: ningún valor de los casos del sondeo produce un error de base de datos;
  los que son inválidos se rechazan en el dominio con un mensaje claro y los demás se
  persisten y se leen de vuelta íntegros (salvo el recorte/saneado documentado).
