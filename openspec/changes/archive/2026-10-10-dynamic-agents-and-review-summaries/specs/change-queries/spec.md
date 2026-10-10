## ADDED Requirements

### Requirement: Reviews ligeras en el canal
Cada elemento de `GET /projects/{slug}/changes` SHALL incluir `reviews`: la lista de las reviews del
`run` actual del change, ordenadas por agente, con únicamente `agent`, `status`, `score`,
`duration_ms` y `run`. Esa lista NUNCA SHALL incluir resumen, hallazgos, error, salida cruda ni el
diff, que se obtienen con `GET /changes/{id}`. Las reviews de runs anteriores SHALL NO aparecer. El
sistema SHALL obtener las de toda la página con una única consulta adicional (sin una consulta por
change) y el campo SHALL ser aditivo: el resto del contrato del listado no cambia.

#### Scenario: Un change con reviews
- **WHEN** un change con una review completada y otra fallida en su run actual aparece en el canal
- **THEN** su `reviews` trae las dos con `agent`, `status`, `score`, `duration_ms` y `run`, y ningún
  texto de resumen, hallazgo, error ni salida cruda

#### Scenario: Tras un reintento
- **WHEN** un change tiene una review fallida en el run 1 y una completada en el run 2 (el actual)
- **THEN** su `reviews` solo contiene la del run 2

#### Scenario: Un change sin reviews
- **WHEN** un change aún no tiene reviews
- **THEN** su `reviews` es una lista vacía

#### Scenario: Sin consulta por change
- **WHEN** el canal devuelve una página de varios changes
- **THEN** las reviews ligeras de toda la página salen de una sola consulta adicional a la base de
  datos, que no lee las columnas de resumen, hallazgos, error ni salida cruda
