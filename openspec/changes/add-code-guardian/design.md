# Design

## Context

Propuesta de partida: un agente "Code Guardian" con instrucciones de sistema (prioriza
errores reales, analiza el contexto, no modifica sin permiso, no inventa bugs, ubica cada
problema, propone soluciones verificables, bloquea lo crítico) y ocho skills especializadas.
Este change conserva esa estructura y la endurece.

## Decisions

**Agente de solo lectura, con `Bash` pero sin `Edit`/`Write`.** Necesita `git diff`,
`git log` y las herramientas del repo (`ruff`, `mypy`, `lint-imports`, `pytest`, `gitleaks`);
no necesita escribir. La regla "no modificar archivos" se cumple por construcción (no tiene
las herramientas de edición) y no solo por instrucción. Las comprobaciones que ejecuta no
deben dejar cambios en el árbol de trabajo (se le pide verificar `git status` al terminar).

**Triaje por riesgo en vez de ejecutar siempre las ocho skills.** `diff-review` va siempre
primero y clasifica el diff (qué capas toca, si hay migraciones, dependencias, CI, API,
tests); solo se cargan las skills que el diff justifica. Evita informes largos y ruido, y es
coherente con "no revisar todo el repositorio sin necesidad".

**Protocolo anti-invención como skill propia (`finding-verification`).** El fallo típico de
un revisor automático es el falso positivo plausible. Cada hallazgo debe llevar evidencia
(línea leída, comando ejecutado, traza de llamada o test que lo reproduce) y una confianza:
`CONFIRMADO` (reproducido o demostrado leyendo el código), `PROBABLE` (consistente con el
código pero no ejecutado) o `HIPÓTESIS`. Las hipótesis nunca cuentan para el veredicto: van
en una sección de preguntas.

**Severidad ligada a puertas de veredicto.** `BLOQUEANTE` (seguridad, pérdida de datos,
regla de capas rota, CI en rojo, workflow no determinista), `IMPORTANTE`, `MENOR`, `NOTA`.
Un solo `BLOQUEANTE` confirmado fija el veredicto en `BLOQUEADO`; el agente no tiene
discreción para suavizarlo.

**Criterios del proyecto dentro de las skills, no en el agente.** Cada skill incluye una
sección "En este repo" con lo que un revisor genérico no sabe (outbox transaccional,
actividades idempotentes con IDs y no diffs, `import-linter`, umbrales de cobertura y
mutación, límites de campo y NUL, `hmac.compare_digest`, SHA pinning de Actions, OpenSpec
obligatorio). Así el agente sigue siendo reutilizable y los criterios viven donde se
mantienen.

**`change-hygiene` y `data-and-api-contracts` como skills nuevas.** Las dos cubren fallos
reales de este repo que ninguna de las ocho originales captura: higiene del commit y del
flujo OpenSpec, y compatibilidad de migraciones y contrato OpenAPI.

**Skill de entrada `guardian` con contexto aislado.** `context: fork` + `agent:
code-guardian` ejecuta la revisión en un subagente y devuelve solo el informe, sin llenar
la conversación principal con la lectura del diff. Con `disable-model-invocation: true`
para que solo se lance cuando el usuario lo pide.

**Idioma.** Informes y skills en español (idioma de la documentación del proyecto);
identificadores, rutas y comandos tal cual.

## Risks / Trade-offs

- [Riesgo] Revisor demasiado ruidoso → Mitigación: triaje por riesgo, confianza explícita,
  hipótesis fuera del veredicto y un máximo de hallazgos por severidad.
- [Riesgo] Falsos positivos que bloquean → Mitigación: un `BLOQUEANTE` exige estado
  `CONFIRMADO`; todo lo demás no bloquea.
- [Riesgo] Las comprobaciones deterministas necesitan Docker/Podman (tests de integración)
  → Mitigación: el agente ejecuta primero lo barato (`just test-unit`, lint) y declara
  explícitamente lo que no pudo ejecutar en vez de darlo por bueno.
- [Riesgo] Las skills envejecen respecto al repo → Mitigación: referencian los comandos
  (`just ...`) y archivos de configuración reales, no copian sus valores, salvo los umbrales,
  que se citan con su origen (`justfile`).

## Open Questions

(ninguna)
