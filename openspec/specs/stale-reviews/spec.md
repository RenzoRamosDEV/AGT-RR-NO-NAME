# stale-reviews Specification

## Purpose
Distinguir una review lenta de una que probablemente se perdió, sin actuar sobre ella.

## Requirements

### Requirement: Marca de diagnóstico stale
El listado `GET /projects/{slug}/changes` y el detalle `GET /changes/{id}` SHALL incluir `stale`
(booleano) en cada change. `stale` SHALL ser verdadero solo si el estado agregado de las reviews
(`review_status`) es `pending` o `running` y han pasado más de `STALE_AFTER_SECONDS` (1800 por
defecto, debe ser mayor que 0) desde el **inicio del `run` actual** (la creación del change para el
primer `run`; el momento del reintento para los siguientes). Los estados `completed`, `failed` y
`partial_failed` NO SHALL marcarse nunca como `stale`. El sistema NO SHALL relanzar ni modificar
nada por ello.

#### Scenario: Pendiente desde hace más del umbral
- **WHEN** un change sin reviews empezó su `run` actual hace más de `STALE_AFTER_SECONDS`
- **THEN** el listado y el detalle muestran `stale: true`

#### Scenario: En curso reciente
- **WHEN** un change `running` empezó su `run` actual hace menos del umbral
- **THEN** muestra `stale: false`

#### Scenario: Reintento sobre un change antiguo
- **WHEN** un change creado hace mucho tiempo se reintenta y su nuevo `run` aún no tiene reviews
- **THEN** muestra `stale: false` hasta que pase el umbral desde el reintento

#### Scenario: Estados terminados
- **WHEN** un change `completed` o `failed` es más antiguo que el umbral
- **THEN** muestra `stale: false`

#### Scenario: Umbral inválido
- **WHEN** `STALE_AFTER_SECONDS` es 0 o negativo
- **THEN** la configuración se rechaza al arrancar
