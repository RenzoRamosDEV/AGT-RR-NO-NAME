---
name: review-report
description: Formato único del informe de revisión de código - escala de severidad, niveles de confianza, plantilla de hallazgo y puertas de veredicto (APROBADO / APROBADO CON NOTAS / CAMBIOS REQUERIDOS / BLOQUEADO). Úsalo al redactar el resultado de cualquier revisión, para que todas se lean igual y sean comparables.
allowed-tools: Read
---

# Informe de revisión

Todas las revisiones terminan con este formato, en español. Sin relleno: si una sección no
tiene contenido, se omite.

## Escala de severidad (impacto si el hallazgo es cierto)

| Severidad | Cuándo |
| --- | --- |
| `BLOQUEANTE` | Secreto expuesto; inyección o salto de autenticación/autorización; pérdida o corrupción de datos; migración irreversible sin plan; rompe la regla de capas (`lint-imports` en rojo); workflow de Temporal no determinista; CI/tests en rojo por el cambio |
| `IMPORTANTE` | Bug funcional con camino real de activación; falta de idempotencia o de transacción donde se exige; test ausente para una rama de negocio nueva; regresión de contrato de API |
| `MENOR` | Defecto acotado o de bajo impacto; deuda de mantenibilidad con coste real |
| `NOTA` | Observación útil que no pide acción (alternativa, contexto, pregunta) |

La **confianza** (`CONFIRMADO`, `PROBABLE`, `HIPÓTESIS`) y la regla de qué puede bloquear se
definen **solo** en `finding-verification`.

## Veredicto (determinista, sin discreción)

1. Algún `BLOQUEANTE` `CONFIRMADO` → **`BLOQUEADO`**.
2. Si no, algún `IMPORTANTE` (`CONFIRMADO` o `PROBABLE`) → **`CAMBIOS REQUERIDOS`**.
3. Si no, algún `MENOR` o `NOTA` → **`APROBADO CON NOTAS`**.
4. Si no → **`APROBADO`**.

**Defecto ya corregido en un commit posterior.** La severidad es la del commit revisado
(no se rebaja), pero el informe da **dos veredictos**: *del commit* (determinista, como
arriba) y *estado actual en HEAD* (calculado sin los hallazgos que HEAD ya corrige, citando
el commit que los corrige). Así un commit antiguo con un defecto remediado se puede leer sin
alarma y sin ocultar que, aislado, era rechazable.

Comprobaciones que no se pudieron ejecutar (matriz de `diff-review`): **no** se dan por
pasadas; se listan en "No verificado" y limitan el veredicto.
- Falta una **obligatoria** → como máximo `CAMBIOS REQUERIDOS` (el cambio no es
  verificable). No es `BLOQUEADO`: falta de evidencia no es un defecto confirmado.
- Falta solo alguna **recomendada** → como máximo `APROBADO CON NOTAS`.

## Plantilla de hallazgo

```
### [SEVERIDAD · CONFIANZA] Título corto y concreto
- **Ubicación:** `ruta/archivo.py:42`
- **Causa:** qué hace el código y por qué está mal (hechos, no opiniones)
- **Impacto:** qué le pasa al sistema o al usuario, y bajo qué condición
- **Evidencia:** línea leída, comando ejecutado y su salida, o traza de llamadas
- **Solución propuesta:** cambio concreto (fragmento de código si ayuda)
- **Cómo verificarla:** test o comando que falla antes y pasa después
```

## Plantilla del informe

```
# Revisión de <objetivo: commit abc123 | PR #n | rama | rutas>

**Veredicto: <VEREDICTO>** (si hay defectos ya corregidos más adelante: *del commit:* X ·
*en HEAD:* Y) · <n> bloqueantes · <n> importantes · <n> menores · <n> notas

## Resumen
2-4 frases: qué cambia, qué riesgo tiene, por qué ese veredicto.

## Comprobaciones ejecutadas
Una fila por comando real (no por receta), indicando sobre qué árbol corrió (commit,
worktree o HEAD).

| Comprobación | Resultado |
| --- | --- |
| `uv run ruff check .` | ✔ / ✖ <resumen> |
| `just test-unit` | ... |
| (lo que se haya ejecutado) | ... |

## Hallazgos
(ordenados por severidad y luego por confianza; plantilla de arriba)

## Preguntas
Hipótesis y dudas que no cuentan para el veredicto, cada una con qué haría falta para
resolverla.

## Skills no cargadas
Solo si el triaje marcaba una skill como aplicable y no se cargó: cuál y por qué.

## No verificado
Lo que no se pudo comprobar y por qué (p. ej. "tests de integración: sin Podman").

## Lo que está bien
Opcional: solo si evita que alguien rompa algo valioso al corregir los hallazgos (p. ej.
"no toques la comparación en tiempo constante"). Sin elogios de cortesía.
```

## Límites para mantener el informe útil

- Máximo 10 hallazgos; si hay más, los 10 más graves y un recuento del resto.
- Un mismo defecto repetido en N sitios es **un** hallazgo con la lista de ubicaciones.
- No comentes estilo que `ruff format`/`biome` ya resuelven.
- Cada hallazgo debe poderse accionar sin preguntar nada más.
