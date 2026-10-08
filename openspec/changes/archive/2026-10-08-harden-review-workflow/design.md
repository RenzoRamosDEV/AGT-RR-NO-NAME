# Design

## Context

`add-review-workflow` dejó funcionando `ReviewChangeWorkflow`/`ReviewCommitWorkflow`. Ver
`proposal.md - Por qué` para los 5 hallazgos de la revisión de Codex (ronda 9); este
documento solo recoge las decisiones de cómo corregirlos.

## Goals / Non-Goals

**Goals:**
- Cumplir de verdad la regla "IDs, no datos, por Temporal" (`openspec/config.yaml`).
- Un solo argumento dataclass por workflow y por activity.
- Que ningún error de configuración desperdicie reintentos.
- Tipar los estados en el dominio.

**Non-Goals:**
- Cambiar el comportamiento observable de `change-review` (sin delta de specs).
- Exponer nada por HTTP ni tocar agentes reales.

## Decisions

**`run_review` carga el `Change` dentro de la activity; se elimina `load_change`.** El
worker `agents` ya necesita acceso a la base de datos para persistir la `Review`, así que
cargar el `Change` ahí no añade ninguna dependencia nueva. La alternativa (mantener
`load_change` en `platform` pero devolver solo metadatos pequeños) añadiría un salto de
red a cada ejecución sin aportar nada: el diff es justo lo que no debe viajar por Temporal.
Consecuencia: la task queue `platform` queda alojando solo workflows por ahora. Es
aceptable y temporal - cuando llegue `prepare_context` (escaneo de secretos con gitleaks y
recorte de diff, Fase 3) volverá a tener una activity propia, y entonces el límite
`platform`/`agents` será real y no decorativo.

**`ReviewChangeInput` y `ReviewCommitInput` como dataclasses de un solo campo-objeto.**
`ReviewChangeInput(change_id, agent_names, run)`. Se mantienen `str`/`int`/`list[str]`
(sin `UUID` ni `datetime`) para no depender de conversores de datos especiales del SDK.

**Agente desconocido = `ApplicationError(non_retryable=True)`, no `Review` fallida.** Un
nombre de agente que no existe en el registro del worker es un error de configuración del
sistema, no un fallo del agente al revisar; persistir una `Review failed` para un agente
que no existe contaminaría las estadísticas futuras (Fase 6). La activity falla rápido y el
workflow lo refleja como fallo.

**`ChangeStatus`/`ReviewStatus` como `StrEnum`.** Igual que `ChangeKind` ya lo es: se
comparan contra strings sin fricción (`review.status == "completed"` sigue siendo cierto)
y los valores guardados en BD no cambian, así que no hay migración.

**`session_scope` se elimina, no se renombra.** Sin uso real, no hay forma de saber qué
forma debería tener cuando se necesite (el endpoint HTTP de `expose-commit-ingestion`
decidirá si hace falta una unidad de trabajo y con qué semántica). Se vuelve a añadir
entonces, con su transacción explícita.

## Risks / Trade-offs

- [Riesgo] Cambiar la firma de los workflows rompería ejecuciones en curso →
  Mitigación: no hay ninguna fuera de los tests (el slice anterior no se desplegó); es el
  momento más barato para corregirlo.
- [Riesgo] `run_review` hace ahora una lectura extra de BD por agente (dos lecturas del
  mismo `Change` por workflow en vez de una) → Mitigación: aceptado, es una lectura por
  clave primaria y evita mover el diff por Temporal; se reevaluará si el perfil real lo
  pide.
