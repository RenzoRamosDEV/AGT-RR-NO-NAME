---
name: bug-detection
description: Detecta errores reales en código modificado - lógica incorrecta, condiciones y límites, nulos, excepciones sin controlar, estado compartido, concurrencia, async y casos límite - con ubicación, impacto, reproducción y solución. Úsalo al revisar lógica nueva o cambiada, o cuando pidan "busca bugs", "¿esto puede fallar?" o "casos límite".
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(uv run pytest:*), Bash(uv run python:*)
---

# Detección de errores

Solo errores con un camino de ejecución real. Cada candidato pasa por `finding-verification`
y se redacta con `review-report`. Salida por bug: **ubicación, impacto, reproducción y
solución propuesta**.

## Lista de comprobación

**Condiciones y límites**
- Off-by-one en rangos, `<` frente a `<=`, cortes de cadenas (`[:n]`), paginación.
- Valores frontera: vacío, un elemento, máximo permitido, máximo + 1, `0`, negativos.
- Lógica booleana: negaciones, `and`/`or` mal precedidos, condiciones inalcanzables o siempre
  verdaderas, comparaciones de float por igualdad.
- `if x:` donde `0`, `""` o `[]` son valores válidos distintos de `None`.

**Nulos y tipos**
- `None` que llega donde se espera un valor (resultados de `get`, `scalar_one_or_none`,
  `dict.get`, campos opcionales). `mypy --strict` ya cubre parte: no repitas lo que ya atrapa.
- Conversiones que lanzan (`int()`, `UUID()`, `datetime` naive frente a aware).
- Texto: encodings, NUL (`\x00` rompe Postgres), Unicode, truncados que parten caracteres.

**Errores y recursos**
- `except Exception` que traga fallos o `except` demasiado estrecho que deja escapar.
- Recursos sin cerrar: sesiones, conexiones, clientes, ficheros; falta de `async with`.
- Reintentos sobre operaciones no idempotentes; errores que deberían ser no reintentables.
- Mensajes de error que ocultan la causa (`raise X` sin `from exc`).

**Estado y concurrencia**
- Comprobar-y-luego-actuar (TOCTOU): `select` y después `insert` sin constraint única.
- Estado mutable compartido entre peticiones o tareas; defaults mutables en funciones.
- `await` olvidado (corrutina sin esperar), tareas lanzadas y no esperadas, bloqueo del
  event loop con código síncrono pesado dentro de `async def`.
- Transacciones: efecto fuera de la transacción que debería ser atómica, commit parcial.

**Contratos entre piezas**
- Un argumento o campo que se acepta pero no se reenvía (en este repo, un patrón real: la
  mutación destapó campos como `agent`, `run` o `diff` que ningún test comprobaba).
- Cambio de firma sin actualizar llamadores, fakes o llamadas por nombre de string.

## En este repo

- **Temporal:** determinismo, versionado, timeouts y reintentos tienen su propia skill:
  `temporal-review`. Aquí solo el efecto en la lógica de negocio.
- **Persistencia:** idempotencia con `INSERT ... ON CONFLICT DO NOTHING RETURNING`, no con
  captura de excepciones. `session.begin()` falla si ya hay una transacción autobegin en la
  sesión (compartir sesión entre repositorios fue un bug real).
- **Texto:** `sanitize_text`/`sanitize_json` antes de escribir; límites en `domain/`
  (`MAX_HEAD_SHA`, `MAX_REF`, `MAX_URL`, ...) alineados con las columnas.

## Cómo reproducir

Prefiere un test mínimo que falle (`uv run pytest tests/unit/... --no-cov -q`) o un
`uv run python -c` con la entrada problemática. Si hace falta Postgres o Temporal y no están
disponibles, el hallazgo queda `PROBABLE` y se anota en "No verificado".
