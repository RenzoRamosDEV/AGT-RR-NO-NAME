---
name: review-report
description: Formato único y breve del informe de revisión de código - estado (APROBADO / REQUIERE CAMBIOS / BLOQUEADO), hallazgos agrupados por dificultad del arreglo (FÁCIL / MEDIO / DIFÍCIL / RECOMENDACIÓN) con la skill que los detectó, y un resumen con recuento, verificaciones y siguiente paso. Úsalo al redactar el resultado de cualquier revisión, para que todas se lean igual y sean comparables.
allowed-tools: Read
---

# Informe de revisión

Todas las revisiones terminan con este formato, en español, lo más breve posible. Si una
sección no tiene contenido, se omite.

## Plantilla

```
# Code Guardian — Code Review

**Estado:** APROBADO | REQUIERE CAMBIOS | BLOQUEADO
**Objetivo:** commit `abc1234` · <título del commit o PR>   (árbol sobre el que corrieron los checks)

## Hallazgos

* **[FÁCIL]** `ruta/archivo.ext:línea` · skill: `bug-detection` · importante
  * **Problema:** una frase, hechos, no opiniones.
  * **Mejora:** la solución en una frase (o el fragmento mínimo).
  * **Evidencia:** una línea: lo leído, el comando y su salida, o la traza.

* **[MEDIO]** `ruta/archivo.ext:línea` · skill: `security-audit` · bloqueante
  ...

* **[DIFÍCIL]** `ruta/archivo.ext:línea` · comprobación: `lint-imports` · importante
  ...

* **[RECOMENDACIÓN]** `ruta/archivo.ext:línea` · skill: `safe-refactoring`
  * **Problema:** oportunidad de mejora identificada.
  * **Mejora:** propuesta opcional.

## Dudas
(Opcional) Hipótesis sin evidencia suficiente, una línea cada una y qué haría falta para
resolverla. No cuentan en el recuento ni en el estado.

## Resumen

**N hallazgos:** a fáciles · b medios · c difíciles · d recomendaciones

**Verificaciones:** ✔ lo ejecutado y pasó · ✖ lo que falló · pendientes: lo que no se pudo
ejecutar y por qué.

**Cómo mejorarlo:** 1-3 pasos en orden (qué arreglar primero y por qué), en una línea cada uno.
```

Reglas del formato:
- Orden de los hallazgos: primero por **estado que provocan** (bloqueante, importante,
  menor) y dentro, por dificultad. Las recomendaciones al final.
- `skill:` es la skill que detectó el hallazgo; si lo detectó una comprobación
  determinista, `comprobación: <comando>`. Si lo vieron varias, la que aportó la evidencia.
- Tras la dificultad y la skill va la **severidad** (`bloqueante`, `importante`, `menor`);
  las recomendaciones no llevan severidad. Si el hallazgo no está `CONFIRMADO`, se añade
  `· probable` (las hipótesis van a "Dudas", nunca a hallazgos).
- Máximo 10 hallazgos; un mismo defecto repetido en N sitios es **uno** con la lista de
  ubicaciones; no comentes estilo que `ruff format`/`biome` ya resuelven.
- Cada hallazgo debe poderse accionar sin preguntar nada más.
- Si hay defectos ya corregidos por un commit posterior, `Estado` lleva dos valores:
  `del commit: X · en HEAD: Y` (el segundo calculado sin esos hallazgos, citando el commit
  que los corrige).
- Si una skill aplicable no se cargó, dilo en `Verificaciones` (cuál y por qué).

## Dificultad (esfuerzo del arreglo; no es la gravedad)

| Etiqueta | Criterio |
| --- | --- |
| `FÁCIL` | Cambio local de pocas líneas en un archivo; sin tocar diseño, contrato ni tests nuevos |
| `MEDIO` | Varios archivos, o exige un test nuevo, regenerar un contrato (`docs/openapi.json`) o coordinar capas |
| `DIFÍCIL` | Cambio de diseño, de esquema o migración, de contrato público, o con una decisión pendiente (quizá un ADR) |
| `RECOMENDACIÓN` | No es un defecto: oportunidad de mejora opcional |

La dificultad y la gravedad son independientes: un secreto expuesto es `FÁCIL` y bloqueante;
una migración arriesgada es `DIFÍCIL` y quizá solo importante.

## Severidad (impacto si el hallazgo es cierto)

| Severidad | Cuándo |
| --- | --- |
| bloqueante | Secreto expuesto; inyección o salto de autenticación/autorización; pérdida o corrupción de datos; migración irreversible sin plan; regla de capas rota (`lint-imports` en rojo); workflow de Temporal no determinista; CI o tests en rojo por el cambio |
| importante | Bug funcional con camino real de activación; falta de idempotencia o de transacción donde se exige; test ausente para una rama de negocio nueva; regresión de contrato de API |
| menor | Defecto acotado o deuda de mantenibilidad con coste real |

La **confianza** (`CONFIRMADO`, `PROBABLE`, `HIPÓTESIS`) y la regla de qué puede bloquear se
definen **solo** en `finding-verification`.

## Estado (determinista, sin discreción)

1. Algún hallazgo **bloqueante** `CONFIRMADO` → **`BLOQUEADO`**.
2. Si no, algún hallazgo **importante** (confirmado o probable), o falta una comprobación
   **obligatoria** (matriz de `diff-review`) → **`REQUIERE CAMBIOS`**. Una obligatoria sin
   ejecutar significa que el cambio no es verificable; no es `BLOQUEADO`, porque la falta de
   evidencia no es un defecto confirmado.
3. Si no → **`APROBADO`**. Los hallazgos menores y las recomendaciones se listan igualmente
   y no impiden aprobar; una comprobación **recomendada** sin ejecutar se anota en
   `Verificaciones` sin cambiar el estado.

Sin hallazgos: `APROBADO` y un `Resumen` de una línea; nada de relleno para justificar la
revisión.
