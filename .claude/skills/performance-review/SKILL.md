---
name: performance-review
description: Detecta problemas de rendimiento reales en un cambio - consultas N+1, complejidad algorítmica, I/O en bucles, fugas de recursos, bloqueo del event loop, payloads grandes por Temporal y contención de concurrencia - explicando siempre el impacto esperado. Úsalo al tocar consultas, bucles con I/O, workflows/activities o rutas calientes, o cuando pidan "revisa el rendimiento".
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(uv run python:*), Bash(uv run pytest:*), Bash(just load:*)
---

# Revisión de rendimiento

**No propongas una optimización sin explicar su impacto esperado** (de qué orden, bajo qué
volumen, medido o estimado y cómo). Optimizar sin un coste demostrado es deuda: este
proyecto es una herramienta personal en local, así que lo que importa son los cuellos de
botella reales (diffs enormes, N reviews en paralelo, consultas sin índice), no los
microajustes.

## Qué buscar

**Base de datos**
- **N+1:** una consulta por elemento dentro de un bucle (`for c in changes: await get(...)`).
  Se arregla con una consulta con `IN`/`JOIN` o carga anticipada.
- **Consultas sin índice** sobre columnas de filtro u ordenación: contrasta con
  `__table_args__` de `models.py` y las migraciones (`ix_changes_project_created_at`,
  `ix_reviews_change_id`). Un `WHERE`/`ORDER BY` nuevo sobre una columna sin índice es un
  hallazgo si la tabla va a crecer.
- `SELECT *` o cargar columnas enormes (`diff`) cuando solo hace falta un id o un contador.
- Transacciones largas que mantienen una conexión abierta mientras se espera a la red,
  a un agente o a Temporal. La transacción debe cubrir solo lo que debe ser atómico.
- Pool de conexiones: sesiones que no se liberan, `engine` creado por petición.

**Algoritmos y memoria**
- Complejidad cuadrática evitable (búsquedas en lista dentro de bucles, `in` sobre `list`).
- Cadenas concatenadas en bucle sobre datos grandes; copias innecesarias de diffs de MB.
- Cargar un fichero o respuesta entera en memoria cuando se puede procesar en flujo.

**Async y concurrencia**
- Código síncrono pesado o bloqueante (`time.sleep`, CPU, `requests`) dentro de `async def`.
- `await` secuenciales de operaciones independientes que podrían ir en `asyncio.gather`;
  o lo contrario: `gather` sin límite sobre miles de tareas.
- Reintentos sin backoff, bucles de espera activa sin tope.

**Recursos**
- Clientes, sesiones, conexiones o procesos hijo sin cerrar; tareas que no se cancelan.
- Cachés sin límite ni expiración.

## En este repo

- **Temporal:** payloads, timeouts y heartbeats: `temporal-review`. Por el historial no
  viaja el diff (límite de 2 MB por payload).
- **Diff acotado:** el recorte (`MAX_DIFF_CHARS`) ocurre antes de persistir; no lo muevas
  después de operaciones costosas.
- **Paralelismo de agentes:** las reviews corren en paralelo por activity; la contención
  está en la base de datos (escrituras idempotentes con `ON CONFLICT`), no en Python.
- **Presupuesto de carga:** `just load` mide `POST /ingest/commit` (0 errores y p95 ≤ 300 ms
  con 5 clientes; referencia actual: p95 ≈ 70 ms). Un cambio en esa ruta que pueda moverlo
  se contrasta ejecutándolo (con la infraestructura arriba) o se anota como "No verificado".

## Cómo reportar

`ubicación` + `por qué es lento` + `escala del problema` (p. ej. "una consulta extra por
review: 2 por commit, irrelevante hoy; con 500 changes por página serían 500") + `arreglo`
+ `cómo medirlo`. Si el impacto es despreciable a la escala del proyecto, es `NOTA` o no
se reporta.
