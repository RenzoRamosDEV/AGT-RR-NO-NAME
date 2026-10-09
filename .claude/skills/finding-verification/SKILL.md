---
name: finding-verification
description: Protocolo anti-invención para revisiones de código - exige evidencia y un nivel de confianza para cada hallazgo antes de reportarlo. Úsalo siempre antes de dar por bueno un hallazgo de cualquier otra skill de revisión, o cuando haya que distinguir un bug real de una sospecha ("verifica este hallazgo", "¿es un falso positivo?", "demuéstralo").
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(git log:*), Bash(git blame:*)
---

# Verificación de hallazgos

Un hallazgo sin evidencia es ruido. Antes de que un hallazgo llegue al informe, pásalo por
este protocolo. Si no lo supera, **no se descarta en silencio: se degrada** a otra confianza
o se mueve a "Preguntas".

> `allowed-tools` en esta y otras skills es una guía de qué usar, no un límite duro: la
> garantía de solo lectura la da el agente `code-guardian` (sin `Edit`/`Write`).

## Los cinco pasos

1. **Localiza.** Abre el archivo y lee las líneas exactas (no te fíes del diff solo: lee
   también el contexto, ~30 líneas alrededor y los llamadores). Cita `ruta:línea`.
2. **Traza.** Sigue el dato desde dónde entra hasta dónde falla: ¿quién llama?, ¿qué valores
   puede recibir de verdad?, ¿hay validación aguas arriba, un `try`, una constraint de BD o
   un tipo que lo impide? Un "posible `None`" que ningún camino produce no es un bug.
3. **Intenta refutarlo.** Busca activamente la razón por la que el hallazgo sea falso: un
   test que lo cubre (`grep` en `tests/`), una regla de `ruff`/`mypy` que ya lo atrapa, un
   comentario o ADR que explique la decisión, el spec de OpenSpec que lo exige.
4. **Reproduce cuando sea barato.** Un test mínimo, un `python -c`, una consulta, un
   `git show`. Si ejecutarlo requiere algo que no tienes (Docker, red), dilo; no lo simules.
5. **Asigna confianza** con los criterios de abajo y redacta la evidencia.

## Niveles de confianza

| Nivel | Criterio | ¿Cuenta para el veredicto? |
| --- | --- | --- |
| `CONFIRMADO` | Reproducido, o demostrado leyendo el código sin ningún camino que lo evite | Sí |
| `PROBABLE` | Consistente con el código leído, con un camino plausible, pero no ejecutado ni demostrado | Sí, hasta `IMPORTANTE`; nunca `BLOQUEANTE` |
| `HIPÓTESIS` | Depende de algo que no se ha podido ver (config de producción, otro repo, datos reales) | No: va a "Preguntas" |

Regla dura: **solo un hallazgo `CONFIRMADO` puede ser `BLOQUEANTE`.**

## Señales de falso positivo (descártalas antes de reportar)

- El código "raro" lo exige un spec (`openspec/specs/`) o un ADR (`docs/adr/`).
- El patrón se repite en todo el repo y está cubierto por tests o por mutación.
- La herramienta del repo (`ruff`, `mypy --strict`, `lint-imports`) ya lo comprueba y pasa.
- Sospechas de una condición de carrera pero hay una constraint `UNIQUE` +
  `ON CONFLICT` o un `workflow_id` determinista que ya la resuelve.
- Lo que parece código muerto lo referencia un registro dinámico (workflows, activities,
  entry points de uvicorn, migraciones de Alembic).

## Lo que nunca hay que hacer

- Reportar un bug por "olor" sin ruta de ejecución.
- Afirmar que algo falla sin haberlo leído o ejecutado.
- Subir la confianza porque "suena grave". La gravedad es el impacto; la confianza, la
  evidencia. Son ejes distintos.
- Decir que se ejecutó algo que no se ejecutó, o dar por pasada una comprobación que se
  saltó.
