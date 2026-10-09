# Tasks

## 1. Plantilla

- [x] 1.1 Reescribir `review-report` con la plantilla nueva, las definiciones de dificultad y
      severidad, y las reglas de estado; verificar que no quedan referencias a la
      plantilla antigua.
- [x] 1.2 Actualizar el agente, las skills y `CONTRIBUTING.md` que citan veredictos o
      severidades; verificar con `grep`.

## 2. Verificación

- [x] 2.1 Prueba real: `code-guardian` sobre un commit y comprobar que el informe sigue la
      plantilla (dificultad, skill detectora, resumen con recuento coherente).
- [x] 2.2 `just ci` y CI de GitHub en verde; archivar.
