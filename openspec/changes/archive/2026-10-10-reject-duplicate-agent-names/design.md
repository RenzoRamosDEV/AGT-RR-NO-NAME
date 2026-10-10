# Design

## Decisiones

1. **Validar en `Settings`** (`config.py`), junto a la regla «al menos un agente»: un
   `field_validator` que compara los nombres con `casefold()` y, si hay repetidos, lanza un error que
   los nombra (el primer duplicado en orden de aparición, con su escritura). Falla al arrancar la API
   y el worker, que comparten `AGENT_NAMES`. No se normaliza la lista: conserva el orden y la
   escritura, porque el worker registra los agentes por nombre y los nombres viajan a Temporal.
2. **`reviews_to_reuse` sin `set` frente a `len`**: exige que cada nombre esperado tenga su review y
   que la lista no tenga repetidos (`len(set(agent_names)) == len(agent_names)`); si los tiene,
   devuelve vacío. Es defensa en profundidad: con la configuración validada no ocurre, pero el dominio
   no debe depender de ello para no dejar una PR en `running` sin workflow.
3. **Índice de `g7d5e9b3c126` sin `CONCURRENTLY`** (aceptado, sin cambio de código): el índice es
   parcial (`WHERE reused_from_change_id IS NOT NULL`) y solo contiene las reviews copiadas, casi
   vacío; el programa es local y con pocas filas, y la migración anterior de índices tampoco lo usó.
   En una base grande conviene crearlo a mano con `CREATE INDEX CONCURRENTLY` antes de migrar.

## Riesgos

- Un despliegue existente con `AGENT_NAMES` repetido pasa a fallar al arrancar: es el comportamiento
  buscado, y el mensaje dice qué nombre corregir.
