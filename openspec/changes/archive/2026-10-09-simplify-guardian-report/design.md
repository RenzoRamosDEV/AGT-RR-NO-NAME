# Design

## Context

Plantilla del usuario: `Estado` + lista de hallazgos etiquetados por dificultad
(`FÁCIL`/`MEDIO`/`DIFÍCIL`/`RECOMENDACIÓN`) con `Problema`/`Mejora` + `Resumen` con recuento
y verificaciones.

## Decisions

**Dos ejes distintos, un solo eje visible por etiqueta.** La *dificultad* (esfuerzo de
arreglar) es lo que el usuario quiere ver agrupado; la *severidad* (impacto si es cierto) es
lo que decide el veredicto. Son independientes: un secreto expuesto es `FÁCIL` de arreglar y
`bloqueante`; una migración riesgosa es `DIFÍCIL` y quizá solo `importante`. La etiqueta
principal es la dificultad; la severidad aparece como una palabra en la misma línea. Sin
severidad no se puede calcular el veredicto de forma determinista, así que no se elimina.

**Dificultad = esfuerzo del arreglo:**
- `FÁCIL`: cambio local de pocas líneas en un archivo, sin tocar diseño ni contrato.
- `MEDIO`: varios archivos, o requiere test nuevo, regenerar un contrato o coordinar capas.
- `DIFÍCIL`: cambio de diseño, de esquema/migración, de contrato público o con decisión
  pendiente (puede necesitar ADR).
- `RECOMENDACIÓN`: no es un defecto; oportunidad de mejora opcional.

**Skill detectora en cada hallazgo.** Hace trazable el informe y permite medir qué skills
rinden. Si lo detectó una comprobación determinista (p. ej. `lint-imports`), se indica
`comprobación: lint-imports`.

**Tres estados.** `BLOQUEADO` (algún bloqueante confirmado), `REQUIERE CAMBIOS` (algún
importante, o falta una comprobación obligatoria), `APROBADO` (el resto; los menores y
recomendaciones se listan pero no impiden aprobar). Una comprobación recomendada que no se
ejecutó se anota en `Verificaciones` sin cambiar el estado.

**Evidencia en una línea, no se quita.** Es lo que impide los falsos positivos
(`finding-verification`); se condensa pero se conserva. Las hipótesis (`HIPÓTESIS`) van a una
línea final opcional `Dudas`, y no cuentan en el recuento ni en el estado.

**Más corto por defecto.** Máximo 10 hallazgos; un defecto repetido es uno solo con lista de
ubicaciones; secciones sin contenido se omiten.

## Risks / Trade-offs

- [Riesgo] Perder la distinción `MENOR`/`NOTA` → Mitigación: lo no accionable es
  `RECOMENDACIÓN`; lo accionable de bajo impacto es hallazgo con severidad `menor`.
- [Riesgo] Dificultad subjetiva → Mitigación: criterios explícitos y verificables (nº de
  archivos, si toca contrato/esquema, si exige test nuevo).

## Open Questions

(ninguna)
