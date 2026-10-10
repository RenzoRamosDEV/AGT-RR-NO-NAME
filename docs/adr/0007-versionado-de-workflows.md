# 0007. Versionado de workflows: parches y replay tests, no Worker Versioning

- Estado: Aceptada
- Fecha: 2026-10-10

## Contexto

Temporal reproduce un workflow desde su historial (*replay*): un cambio en la secuencia de
comandos (activities, hijos, timers) rompe las ejecuciones en vuelo con un error de no
determinismo. La documentación oficial recomienda **Worker Versioning** por defecto (cada
Workflow Type anotado como *Pinned* o *Auto-Upgrade*, con despliegues de varias versiones de
worker a la vez) y deja **patching** (`workflow.patched` / `deprecate_patch`) como alternativa
cuando no hay despliegues *blue-green* o *rainbow*.

En Duelo hay un worker por task queue, en la máquina del usuario (`just worker`), porque los CLI
de los agentes están autenticados ahí; no existe infraestructura para mantener dos versiones de
worker en paralelo ni un servidor con *Worker Deployments* configurados. Los workflows duran
minutos y tienen pocas decenas de eventos. Ya hay dos marcadores de parche
(`compensate-infra-failure`, `readable-workflow-names`) y replay tests sobre historias grabadas
(`backend/tests/integration/workflows/legacy_*.py`).

## Decisión

1. **Semántica Auto-Upgrade.** Una ejecución en vuelo pasa al código nuevo cuando se reinicia el
   worker; el código nuevo debe reproducir cualquier historial anterior. **No se declara al SDK**
   con `versioning_behavior`: sin un `deployment_config` (Worker Versioning) el servidor real
   rechaza cada activación con «deployment must be set when versioning behavior specified»,
   aunque el servidor de test (time-skipping) la acepte — se comprobó al revés en una primera
   versión de este ADR y rompió las reviews. Cualquier opción nueva de `@workflow.defn` o del
   `Worker` se valida contra el servidor real (`just dev` + `just worker`) antes de integrarla.
2. **Cada cambio de comandos va bajo `workflow.patched("<marcador>")`** con un replay test que
   reproduce una historia grabada con el código anterior (`handle.fetch_history()` guardada en
   `tests/integration/workflows/`). Sin esa historia el cambio no se considera seguro.
3. **Retirada de marcadores.** Cuando no quede ninguna ejecución anterior al marcador (en local
   basta con que no haya workflows en curso en la UI de Temporal), se pasa a
   `workflow.deprecate_patch` y, en un cambio posterior, se elimina; la historia grabada se
   conserva mientras exista el marcador.
4. **Cambios seguros sin parche**: opciones de reintento y timeouts de activities, campos nuevos
   en los DTO con valor por defecto, resúmenes y detalles de usuario.
5. **No se adopta Worker Versioning.** Se revisará si Duelo llega a desplegarse con varios workers
   por cola o en Temporal Cloud; entonces convendría *Pinned* para estos workflows cortos.

## Consecuencias

- Los replay tests son parte de la suite de integración y corren en CI; el checklist de
  `docs/temporal-buenas-practicas.md` exige parche + historia grabada en cualquier PR que toque
  los comandos.
- Un worker antiguo nunca convive con uno nuevo: al reiniciar `just worker` todas las
  ejecuciones en vuelo pasan al código nuevo, de ahí que *Auto-Upgrade* sea la única semántica
  posible hoy.
- Los marcadores de parche se acumulan si no se retiran; la regla 3 fija cuándo hacerlo.
