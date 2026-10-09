# Design

## Context

Ver `proposal.md - Por qué`. La API solo ingiere commits; el modelo de datos ya contiene
todo lo necesario (`ChangeKind.PR`, `reviews`, índice `(project_id, created_at)`), así que
este change es sobre todo exponer lecturas y generalizar la ingesta.

## Goals / Non-Goals

**Goals:**
- Cinco endpoints nuevos con contrato estable y testeado (snapshot + schemathesis).
- Ningún cambio de esquema ni de comportamiento de `POST /ingest/commit`.
- Lecturas que no cargan diffs enteros cuando no se necesitan.

**Non-Goals:**
- Autenticación de lecturas, webhooks de GitHub, debounce de PRs, SSE, frontend.

## Decisions

**Las lecturas no exigen token (desviación consciente).** `X-Ingest-Token` protege la
*ingesta* (quien escribe). El frontend es un cliente de navegador sin login, y el producto
es una herramienta personal en `127.0.0.1` (`openspec/config.yaml`: sin multiusuario). Poner
el token en el navegador sería publicarlo. Trade-off: cualquiera que alcance la API lee
diffs. Mientras la API solo escuche en local es aceptable; antes de exponerla hay que añadir
autenticación de lectura (candidato a ADR).

**Modelos de lectura propios en `application/read_models.py`.** `ChangeSummary` (un `Change`
sin diff), `ChangeCursor`, `ChangePage`, `ChangeDetail` y `AgentStats` son datos de consulta,
no entidades de dominio. Los puertos los devuelven directamente; así el canal no carga el
diff (hasta 200 000 caracteres por fila) y el dominio no se contamina con proyecciones.

**Paginación por cursor (keyset) sobre `(created_at, id)`, no por offset.** El offset
repite o salta elementos si entran changes nuevos mientras se pagina, y degrada con la
profundidad. Se ordena por `created_at DESC, id DESC` y el cursor es el par del último
elemento devuelto; `id` desempata los changes con el mismo instante. El puerto
`list_for_project` devuelve a lo sumo `limit` elementos posteriores al cursor; el caso de uso
pide `limit + 1` para saber si hay más y construye `next_cursor`. El cursor viaja como
base64url de `"{created_at ISO}|{id}"`, opaco para el cliente; la codificación vive en
`entrypoints/api/cursor.py` porque es un detalle del transporte HTTP. Uno mal formado es 422.

**`ingest_commit` y `ingest_pr` comparten una función interna parametrizada por `ChangeKind`.**
`CommitSubmission` pasa a llamarse `ChangeSubmission` con el alias `CommitSubmission` para no
romper imports. El request HTTP de PR hereda el de commit: mismos campos y límites (en un PR,
`ref` es la rama o `refs/pull/N/head` y `head_sha` el último commit de la cabeza).

**El workflow id lleva el `kind`: `{kind}-{project_id}-{head_sha}`.** Para commits sigue
siendo `commit-...`, así que las ejecuciones en vuelo no cambian. Sin el `kind`, un PR y un
commit con el mismo sha chocarían en Temporal aunque sean changes distintos. Se reutiliza
`ReviewCommitWorkflow` (padre genérico por `change_id`); renombrarlo no merece el riesgo de
versionado de workflows en vuelo.

**Estadísticas por agente con una única consulta agregada** (`GROUP BY agent`, `COUNT ... FILTER`,
`AVG` ignoran los `NULL`). Duración y score medios sobre las reviews que tienen valor; se
devuelven como `float | None`. Sin índice nuevo: el volumen de un usuario local no lo
justifica; se revisará si crece.

**Una sesión por lectura en la composición.** Igual que la ingesta: cada callable de
`ApiDependencies` abre y cierra su sesión, y los repositorios de lectura no mantienen
transacciones abiertas.

## Risks / Trade-offs

- [Riesgo] Lecturas sin autenticación → Mitigación: documentado arriba; la API escucha en
  `127.0.0.1` por defecto.
- [Riesgo] Cursor tras borrar el change al que apunta → Mitigación: es una posición
  `(created_at, id)`, no una referencia; sigue siendo válido.
- [Riesgo] `GET /projects/{slug}/changes` con slugs que contienen `/` (`acme/widgets`) →
  Mitigación: parámetro de ruta `{slug:path}` y test con un slug con barra.
- [Riesgo] Un PR actualizado (nuevo `head_sha`) crea otro change y otra review → Aceptado:
  el debounce es de la Fase 5 del spec.

## Open Questions

(ninguna)
