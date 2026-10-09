# Design

## Context

Los límites de longitud ya existen de facto en las columnas (`changes.head_sha` 64,
`ref` 255, `url` 1000, `title` 500, `author` 255, `reviews.agent` 50), pero el dominio no
los conoce: `Change.new` solo valida que `head_sha` no sea vacío. Ver `proposal.md` para el
sondeo que lo demostró.

## Goals / Non-Goals

**Goals:**
- Que ninguna entrada produzca un error de base de datos opaco: o se rechaza pronto con un
  mensaje claro, o se acepta y se persiste.
- Que los límites no puedan derivar entre dominio y esquema sin que un test falle.

**Non-Goals:**
- Mapear los rechazos a HTTP (lo hará la API).
- Cambiar los límites de las columnas ni migrar nada.

## Decisions

**Rechazar identificadores, recortar metadatos.** `head_sha`, `ref` y `url` son
identificadores/enlaces: un valor recortado apuntaría a otro commit o a una URL rota, así
que se rechazan con `ValueError` nombrando el campo. `title` y `author` solo se muestran:
rechazar un commit por un asunto de 501 caracteres perdería su review (el hook de commit
es en segundo plano y nunca bloquea al usuario, así que el rechazo sería silencioso), por
eso se recortan. Alternativa descartada: rechazarlo todo por uniformidad - más simple, pero
pierde reviews legítimas.

**Las constantes de límite viven en el dominio y un test las ata al esquema.** El límite
es una regla de negocio ("un asunto tiene como mucho 500 caracteres") que casualmente
coincide con la columna. Un test unitario lee `ChangeModel.__table__.c.<col>.type.length`
y falla si divergen: así cambiar una columna sin tocar el dominio (o al revés) no pasa
desapercibido. Alternativa descartada: derivar las constantes del modelo SQLAlchemy -
metería el esquema en el dominio y rompería la regla de capas.

**El saneado de NUL vive en los adaptadores, no en el dominio.** Que Postgres no admita
`\x00` es una limitación del almacenamiento, no una regla de negocio; el dominio sigue
aceptando cualquier texto. Un helper `sanitize_text` / `sanitize_json` en
`adapters/persistence/sanitize.py` reemplaza NUL por `U+FFFD` justo antes de insertar.
Se elige sustituir (y no eliminar) para que el hueco sea visible al leer el contenido.
`head_sha`/`ref`/`url` no pasan por el saneado: con NUL ya se rechazan en el dominio.

**El JSONB de `findings` también se sanea.** Postgres rechaza `\u0000` dentro de `jsonb`,
así que `sanitize_json` recorre recursivamente cadenas en dicts y listas.

**`hypothesis` para el saneado y el recorte.** Son funciones puras con una propiedad
clara ("para cualquier cadena, el resultado no contiene NUL; es idempotente; si la
entrada no tenía NUL no cambia" y "el recorte nunca excede el límite y conserva el
prefijo"). Ahí los ejemplos fijos dejan huecos y la generación aleatoria sí aporta. No se
usa para el resto de la lógica, donde un ejemplo explícito es más legible.

## Risks / Trade-offs

- [Riesgo] Recortar `title` pierde información silenciosamente → Mitigación: aceptado y
  documentado en el spec; 500 caracteres cubre con holgura cualquier asunto razonable.
- [Riesgo] Un `head_sha` de más de 64 caracteres legítimo (algún hash futuro) → Mitigación:
  SHA-1 son 40 y SHA-256 son 64; el límite cubre ambos, y ampliar la columna sería una
  migración explícita con su propio change.
- [Riesgo] Sustituir NUL altera el diff guardado → Mitigación: el cambio es mínimo y
  visible (`U+FFFD`); un diff con NUL es en la práctica binario y no revisable de todos
  modos.
