# Spec Delta

## ADDED Requirements

### Requirement: Filtros del canal por estado de review y texto
El sistema SHALL aceptar en `GET /projects/{slug}/changes` el parámetro `status` (repetible,
con los valores `pending`, `running`, `partial_failed`, `failed` y `completed`) y el parámetro
`q`, y devolver solo los changes cuyo `review_status` esté entre los indicados y cuyo título,
autor, SHA o ref contengan `q` sin distinguir mayúsculas. Los filtros SHALL combinarse entre sí
y con `kind`, y SHALL respetar la paginación por cursor. Los caracteres `%`, `_` y `\` de `q`
SHALL tratarse como texto literal. Un `q` vacío tras recortarlo SHALL ignorarse; un `q` con NUL o de
más de 100 caracteres, o un `status` desconocido, SHALL responder 422.

#### Scenario: Filtro por estado
- **WHEN** el canal tiene changes `completed` y `failed` y se pide `status=failed`
- **THEN** solo se devuelven los `failed`

#### Scenario: Varios estados
- **WHEN** se pide `status=pending&status=running`
- **THEN** se devuelven los changes en cualquiera de los dos estados

#### Scenario: Búsqueda por texto
- **WHEN** se pide `q=ReNzO` y solo un change tiene ese autor, en cualquier capitalización
- **THEN** solo se devuelve ese change; lo mismo ocurre al buscar un fragmento del título, del
  SHA o del ref

#### Scenario: Comodines literales
- **WHEN** se pide `q=50%` y un change tiene "50% más rápido" en el título y otro "500 casos"
- **THEN** solo se devuelve el primero

#### Scenario: Filtros con paginación
- **WHEN** hay cinco changes que cumplen `status=failed` y se pide `limit=2` encadenando `next_cursor`
- **THEN** se recorren los cinco, sin repetir ni omitir, y ninguno de otro estado

#### Scenario: Parámetros inválidos
- **WHEN** se envía `status=desconocido` o un `q` con NUL
- **THEN** la respuesta es 422

### Requirement: Estado agregado de las reviews de un change
El sistema SHALL incluir en cada change del canal y en su detalle el campo `review_status`,
calculado sobre las reviews del `run` actual del change frente al número de agentes configurados:
`pending` si no hay ninguna; `running` si hay menos que agentes; y, con todas registradas,
`completed` si ninguna falló, `failed` si todas fallaron y `partial_failed` en otro caso. Las
reviews de runs anteriores NO SHALL contar.

#### Scenario: Sin reviews
- **WHEN** un change recién ingerido no tiene reviews
- **THEN** su `review_status` es `pending`

#### Scenario: Faltan agentes
- **WHEN** hay dos agentes configurados y solo uno ha registrado su review, completada o fallida
- **THEN** el `review_status` es `running`

#### Scenario: Todas registradas
- **WHEN** ambos agentes han registrado su review
- **THEN** es `completed` si ninguna falló, `failed` si fallaron las dos y `partial_failed` si
  falló una

#### Scenario: Un reintento reinicia el estado
- **WHEN** el change avanza a `run = 2` y aún no hay reviews de ese run
- **THEN** su `review_status` es `pending`, aunque el run 1 tuviera reviews

### Requirement: Resumen de findings de un change
El sistema SHALL incluir en el detalle de un change `findings_summary` con `total` y
`by_severity` (`bug`, `risk`, `improvement`, `nit`, `other`), contando los findings de las
reviews completadas del `run` actual. Las severidades SHALL normalizarse (sin distinguir
mayúsculas ni espacios, con sinónimos conocidos) y las desconocidas contarse como `other`. La
respuesta NO SHALL incluir la salida cruda del agente.

#### Scenario: Findings de varias reviews
- **WHEN** dos reviews del run actual aportan tres findings `bug`, `Risk` y `nit`
- **THEN** `total` es 3 y `by_severity` cuenta uno en `bug`, uno en `risk` y uno en `nit`

#### Scenario: Severidad desconocida
- **WHEN** un finding tiene severidad `"banana"`
- **THEN** cuenta en `other` y el `total` lo incluye

#### Scenario: Sin findings
- **WHEN** el change no tiene reviews completadas con findings
- **THEN** `total` es 0 y todos los contadores son 0

#### Scenario: Runs anteriores
- **WHEN** el change está en `run = 2` y las reviews del run 1 tenían findings
- **THEN** esos findings no cuentan
