# worker-operations Specification

## Purpose
Define cómo se opera el worker de Temporal de Duelo: cómo se apaga sin perder trabajo, en qué
namespace trabaja y qué métricas expone para vigilarlo.

## Requirements

### Requirement: Apagado ordenado del worker
Al recibir `SIGTERM` o `SIGINT`, el worker SHALL dejar de aceptar tareas nuevas, SHALL esperar a
las activities en curso hasta un plazo de gracia configurable (`WORKER_SHUTDOWN_GRACE_SECONDS`,
30 s por defecto), SHALL cancelarlas al vencer ese plazo y SHALL terminar con código de salida 0.
Una review interrumpida así SHALL reintentarse por la política de reintentos habitual cuando
vuelva a haber un worker; NO SHALL quedar registrada como completada ni fallida por el apagado.

#### Scenario: Señal sin trabajo en curso
- **WHEN** el worker recibe `SIGTERM` sin ninguna activity en ejecución
- **THEN** termina de inmediato con código 0

#### Scenario: Señal con una review en curso que no termina a tiempo
- **WHEN** el worker recibe `SIGTERM` mientras un agente revisa y la review no termina dentro del
  plazo de gracia
- **THEN** la llamada al agente se cancela, el worker termina, y al arrancar otro worker la review
  se vuelve a ejecutar y queda persistida una sola vez

#### Scenario: Señal con una review que termina dentro del plazo
- **WHEN** el worker recibe `SIGTERM` y la review en curso termina antes de agotar el plazo
- **THEN** la review queda persistida y el worker termina sin cancelarla

### Requirement: Namespace configurable
La API y el worker SHALL hablar con Temporal en el namespace indicado por `TEMPORAL_NAMESPACE`
(`default` si no se define), de modo que los dos procesos de un mismo entorno usen el mismo.

#### Scenario: Sin configurar
- **WHEN** no se define `TEMPORAL_NAMESPACE`
- **THEN** la API y el worker usan el namespace `default`

#### Scenario: Namespace de otro entorno
- **WHEN** se define `TEMPORAL_NAMESPACE=staging`
- **THEN** el cliente de la API y el del worker se conectan a `staging`

### Requirement: Métricas del worker opcionales
Si se define `TEMPORAL_METRICS_ADDRESS` (`host:puerto`), el worker SHALL exponer en esa dirección,
en formato Prometheus, las métricas del SDK de Temporal (al menos la latencia schedule-to-start de
workflows y activities, los slots de tareas disponibles y los fallos de peticiones al servidor).
Sin la variable NO SHALL abrir ningún puerto.

#### Scenario: Métricas activadas
- **WHEN** el worker arranca con `TEMPORAL_METRICS_ADDRESS=127.0.0.1:9464` y procesa una review
- **THEN** `GET http://127.0.0.1:9464/metrics` responde en formato Prometheus con métricas
  `temporal_*` del worker

#### Scenario: Métricas desactivadas
- **WHEN** el worker arranca sin `TEMPORAL_METRICS_ADDRESS`
- **THEN** no escucha en ningún puerto de métricas
