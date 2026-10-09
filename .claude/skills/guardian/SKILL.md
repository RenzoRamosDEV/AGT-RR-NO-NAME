---
name: guardian
description: Lanza una revisión completa con el agente code-guardian sobre un commit, rango, rama, Pull Request o ruta, en un contexto aislado, y devuelve solo el informe con veredicto. Úsalo con /guardian para revisar el último commit, "/guardian HEAD~3..HEAD", "/guardian 42" (PR) o "/guardian backend/src/review_arena/application".
argument-hint: "[commit | rango | nº de PR | ruta]"
disable-model-invocation: true
context: fork
agent: code-guardian
---

Revisa el siguiente objetivo siguiendo tu flujo completo (delimitar, triaje con
`diff-review`, comprobaciones deterministas, análisis con las skills que el riesgo
justifique, verificación de cada hallazgo y informe con el formato de `review-report`):

**Objetivo:** $ARGUMENTS

Si el objetivo está vacío, revisa el último commit de la rama actual e indícalo en el
informe. Un número solo (p. ej. `42`) es un Pull Request de este repositorio; un rango
contiene `..`; una ruta existe en el árbol de trabajo; lo demás se trata como un commit.

No modifiques ningún archivo. Termina con el informe y nada más.
