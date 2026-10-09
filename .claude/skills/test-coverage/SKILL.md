---
name: test-coverage
description: Evalúa la calidad de las pruebas de un cambio - cobertura de ramas, pruebas significativas (no de relleno), casos límite, clases de equivalencia, valores límite, regresión, mutación, tests frágiles o lentos. Úsalo al revisar código nuevo o cambiado, o cuando pregunten "¿está bien testeado?" o "¿faltan tests?".
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(uv run pytest:*), Bash(uv run coverage:*), Bash(uv run mutmut:*), Bash(just test-unit:*), Bash(just mutation:*)
---

# Calidad de las pruebas

Mide si los tests **detectarían un fallo**, no cuántos hay. Este repo lo demostró: cobertura
del 99 % con una mutación del 71 %. La regla del proyecto es "solo tests con sentido; lo
diferido se documenta con motivo" (`docs/testing.md`).

## 1. Qué se esperaba y qué hay

Para cada pieza de lógica nueva o modificada, ¿qué comportamiento tiene que cumplir y
qué test lo fija? Empieza por el código de producción del diff y busca su test
(`Grep` por nombre en `tests/`). Anota lo que **no** tiene test.

## 2. Comprobaciones deterministas

- `just test-unit` (segundos, sin Docker) para feedback inmediato.
- `just test` aplica los umbrales: cobertura global ≥ 97 % y `domain`+`application` = 100 %
  (líneas + ramas, `--cov-branch`). Los valores viven en el `justfile`; no los copies.
- `just mutation` (mutmut sobre `domain`+`application`, umbral 95 %, hoy 100 %): para un
  cambio en esas capas, un mutante superviviente es un assert débil, y se reporta con el
  mutante concreto (`uv run mutmut results`).
- Necesitan Podman/Docker: `test-integration` y `just ci`. Si no están, "No verificado".

## 3. Qué hace buena una prueba

- **Falla por la razón correcta:** si rompieras el código de producción, ¿falla este test?
  Un test que repite la implementación o solo comprueba que "no lanza" no protege nada.
- **Asserts sobre el resultado observable** (valor devuelto, fila persistida, evento
  emitido), no sobre llamadas internas. Cuando algo se persiste, comprueba la **fila real**,
  no solo el objeto devuelto.
- **Un comportamiento por test**, con nombre que lo describe.
- **Sin dependencias ocultas:** orden, hora, red, aleatoriedad sin semilla, sleeps fijos.
  Espera condiciones (con tiempo máximo y diagnóstico), no duermas a ciegas.
- **Fakes fieles:** un fake que deduplica o falla como el real; si divergen, el test
  verde engaña.

## 4. Técnicas, cuando aportan

| Técnica | Cuándo exigirla |
| --- | --- |
| Clases de equivalencia | Entradas con comportamientos distintos por tramo (tipos, estados) |
| Valores límite | Cualquier límite numérico o de longitud: `límite-1`, `límite`, `límite+1` |
| Tabla de decisión | Varias condiciones combinadas deciden el resultado |
| Transiciones de estado | Hay máquina de estados con transiciones válidas e inválidas |
| Propiedad (hypothesis) | Invariantes, round-trips, leyes de idempotencia |
| Regresión | Todo `fix`: un test con marcador `regression` y el origen en el docstring |
| Negativos | Entrada inválida, dependencia caída, dato ausente, permiso denegado |

No pidas una técnica que no aporta: "no metas test por meter" es regla del repo. Un test
redundante o de relleno es un hallazgo menor (candidato a borrar o fusionar).

## 5. Dónde va cada test (`docs/testing.md`)

- Lógica pura sin I/O → `tests/unit/` (domain/application sin importar adapters).
- Postgres o Temporal → `tests/integration/<tema>/`.
- Flujo completo por HTTP → `tests/e2e/`.
- Contrato de API → `tests/unit/contract/` (snapshot + schemathesis).
- Un test de integración puesto donde bloquea mutmut, o un test unitario que necesita
  Docker, está mal ubicado.

## 6. Fragilidad y coste

Marca tests con `sleep` fijo, asserts de igualdad exacta sobre conteos de eventos
asíncronos (usa `>=` y diagnóstico), dependencia de puertos fijos, de orden entre tests o de
datos de otro test (datos compartidos en una base común: filtra por el id propio).

## Salida

Lista de comportamientos sin test (con el test que propones y en qué carpeta), tests
débiles o frágiles (con el mutante o escenario que los vence) y el estado de los umbrales.
