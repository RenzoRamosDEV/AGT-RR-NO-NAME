---
name: data-and-api-contracts
description: Revisa migraciones de base de datos, deriva entre modelos y esquema, transacciones e idempotencia, y la compatibilidad del contrato de la API (OpenAPI, códigos de estado, schemas). Úsalo al tocar alembic/, models.py, repositorios, routers, schemas o docs/openapi.json, o cuando pregunten "¿rompe esto el contrato?" o "¿es segura esta migración?".
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(uv run pytest:*), Bash(uv run alembic:*), Bash(just openapi:*)
---

# Datos y contratos de API

Cubre dos superficies donde un error se paga caro y tarde: el esquema de datos y el contrato
público.

## Migraciones (Alembic, escritas a mano)

- **Cada cambio de modelo trae su migración** y viceversa. `tests/integration/persistence/
  test_migrations.py` compara modelos y migraciones con `compare_metadata`: si ese test
  falla, la deriva es `CONFIRMADA`. Índices, `UNIQUE` y constraints cuentan (ya hubo deriva
  real por no declararlos en los modelos).
- **Reversibilidad:** `downgrade()` implementado y probado (`upgrade` → `downgrade` →
  `upgrade`). Una migración irreversible sin plan es `BLOQUEANTE`.
- **Seguridad de los datos:** `NOT NULL` sin valor por defecto sobre una tabla con datos,
  borrar o renombrar una columna en uso, cambiar tipos con pérdida, `DROP` sin copia. Pasos
  seguros: añadir nullable → rellenar → imponer; o expandir/contraer en dos despliegues.
- **Bloqueos:** `CREATE INDEX` sin `CONCURRENTLY` y `ALTER TABLE` pesados sobre tablas
  grandes bloquean escrituras; irrelevante en una tabla vacía, relevante en producción.
- **Orden y cadena:** una única cabecera de revisiones (`alembic heads` = 1), sin ramas.
- Longitudes de columna y constantes del dominio (`MAX_*`) coinciden; hay un test que lo
  comprueba (`test_limits_match_schema.py`).

## Persistencia, transacciones e idempotencia

- Lo que debe ser atómico va en **una** transacción: la fila y su evento del outbox
  (`events`) se escriben juntas o no se escribe nada.
- Idempotencia por clave natural con `UNIQUE` + `INSERT ... ON CONFLICT DO NOTHING
  RETURNING`; no con "consultar y luego insertar". Reintentar debe ser seguro.
- No compartas una `AsyncSession` entre repositorios que abren `session.begin()`: la
  lectura autobegin deja una transacción abierta y el siguiente `begin()` falla.
- Datos de texto: saneados (NUL) y dentro de los límites antes de llegar a la base.
- Si añades una consulta nueva: ¿índice?, ¿paginación?, ¿orden determinista?

## Contrato de la API (OpenAPI)

El snapshot `docs/openapi.json` es el contrato versionado; `tests/unit/contract/` lo compara
con la app y ejecuta `schemathesis`. Un cambio de contrato es deliberado: se regenera con
`just openapi` y se revisa el diff.

- **Cambios incompatibles (hacia atrás):** quitar o renombrar un campo, endurecer una
  validación (más `min_length`, `extra="forbid"` nuevo), cambiar un tipo, un código de
  estado o un nombre de cabecera, hacer obligatorio un campo opcional. Si hay clientes
  (hook local, cliente TS generado), es `IMPORTANTE` salvo versionado o migración documentada.
- **Cambios compatibles:** campos opcionales nuevos, respuestas nuevas documentadas.
- **Todos los códigos de estado reales están documentados** en `responses` (un 400 sin
  documentar ya lo encontró `schemathesis`). Un handler que lanza un status que el contrato
  no declara es un bug de contrato.
- **Mapa de errores coherente:** 401 sin credencial, 404 recurso inexistente, 422 entrada
  inválida, 503 dependencia caída; el cuerpo de error no filtra detalles internos.
- **Schemas como fuente de verdad:** los límites de Pydantic salen de las constantes del
  dominio (`MAX_*`), no se duplican como números sueltos.
- **Cliente TS generado:** cuando exista (`just gen-client` es hoy un marcador hasta la
  Fase 4), un cambio de contrato obliga a regenerarlo y CI debe fallar ante deriva; hasta
  entonces, comprueba si el frontend ya consume el endpoint cambiado.
- **Idempotencia del endpoint:** reenviar la misma petición devuelve el mismo recurso y no
  duplica efectos.

## Cómo verificar

`uv run pytest tests/unit/contract --no-cov -q` (contrato) y, con Podman,
`tests/integration/persistence` (esquema y migraciones). Si no puedes ejecutarlos, el
hallazgo queda `PROBABLE` y se anota en "No verificado".
