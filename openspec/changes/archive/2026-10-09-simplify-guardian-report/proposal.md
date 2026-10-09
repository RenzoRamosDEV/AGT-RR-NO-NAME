# Proposal

## Por qué

El informe de `code-guardian` (plantilla de `review-report`) es largo: seis campos por
hallazgo, ocho secciones y cuatro veredictos. El usuario quiere un informe corto que se lea
de un vistazo y que diga, por cada hallazgo, **qué skill lo detectó**, **cuánto cuesta
arreglarlo** (fácil, medio o difícil) o si es solo una recomendación, y cierre con un
resumen y cómo mejorar, también breve. Aportó una plantilla base.

## Qué cambia

- **Nueva plantilla de informe** (basada en la del usuario): `Estado` con tres valores
  (`APROBADO`, `REQUIERE CAMBIOS`, `BLOQUEADO`), hallazgos agrupados por dificultad del
  arreglo (`FÁCIL`, `MEDIO`, `DIFÍCIL`, `RECOMENDACIÓN`) y `Resumen` con el recuento, las
  verificaciones y el siguiente paso.
- **Cada hallazgo** muestra `ruta:línea`, la **skill que lo detectó**, su severidad
  (bloqueante / importante / menor) y, si no está confirmado, su confianza; con
  `Problema` y `Mejora` en una frase y una línea de `Evidencia` (el anti-invención se
  mantiene).
- **Definición de dificultad** (esfuerzo del arreglo, ortogonal a la severidad).
- Veredicto de tres estados con reglas deterministas actualizadas; desaparece
  `APROBADO CON NOTAS` (lo que antes eran notas ahora son hallazgos menores o
  recomendaciones dentro de `APROBADO`).
- Se actualizan las referencias en el agente, las skills y `CONTRIBUTING.md`.

## Capacidades

Ninguna (tooling de proceso, `skip_specs: true`).

## Impacto

`.claude/skills/review-report/SKILL.md`, `.claude/agents/code-guardian.md`, referencias en
otras skills y `CONTRIBUTING.md`. Sin código del producto.
