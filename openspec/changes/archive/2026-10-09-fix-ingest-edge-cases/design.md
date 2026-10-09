# Design

## Context

Ver `proposal.md`. Dos correcciones acotadas sobre `expose-commit-ingestion`.

## Decisions

**`ALLOW_DUPLICATE_FAILED_ONLY` en vez de `REJECT_DUPLICATE`.** `REJECT_DUPLICATE` también
bloquearía el reintento de un commit cuya ejecución falló (agentes caídos, worker ausente
hasta agotar reintentos); el usuario reenviaría y no pasaría nada. Con
`ALLOW_DUPLICATE_FAILED_ONLY` una ejecución completada no se repite y una fallida sí puede
repetirse. La segunda barrera de idempotencia sigue siendo el workflow id determinista.

**Doble defensa para NUL en `project`.** El schema lo rechaza en el borde (422 con el
formato estándar de validación). El repositorio devuelve `None` ante un slug con NUL como
defensa en profundidad, para que otro llamador futuro no reintroduzca el 500; el router lo
convertiría en 404, que es correcto (ningún proyecto puede llamarse así).

**No se amplía el `except ValueError` del router** (sugerido en la revisión como MENOR):
queda fuera de este change y se anota como mejora independiente.

## Risks / Trade-offs

- [Riesgo] Un workflow completado con resultado parcial (un agente falló) no se relanza al
  reenviar → Mitigación: es el comportamiento pedido por el spec ("sin duplicar trabajo");
  relanzar a propósito será una acción explícita (`run` + 1) cuando exista.

## Open Questions

(ninguna)
