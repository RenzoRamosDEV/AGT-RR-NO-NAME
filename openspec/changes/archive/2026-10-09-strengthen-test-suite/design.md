# Design

## Context

Estado medido antes de empezar: 96 tests, 99 % de cobertura de líneas y ramas, mutación
~71 % sobre `domain/`+`application/` (206 mutantes, 59 vivos), un único `conftest.py` raíz
con fixtures de contenedor, y hallazgos reales ya corregidos en `harden-input-limits`
(límites de columna y NUL). Ver `proposal.md`.

## Goals / Non-Goals

**Goals:**
- Que los tests detecten regresiones reales (puntuación de mutación) y no solo ejecuten
  líneas (cobertura).
- Feedback rápido: la capa unitaria corre en segundos sin Docker.
- Cubrir cada punto del checklist con un test que aporte, o dejar escrito por qué no aplica.

**Non-Goals:**
- Tests de API HTTP, autenticación, seguridad de API, E2E por HTTP y carga: no existe aún
  el código que probar (`expose-commit-ingestion`).
- Perseguir 100 % de mutación: habrá mutantes equivalentes; se fija un umbral realista.

## Decisions

**Dos capas por directorio: `tests/unit` y `tests/integration`.** Unit = sin red, sin
Docker, sin base de datos (fakes y sesiones simuladas); integration = Postgres real
(testcontainers) y/o el entorno de test de Temporal. Los fixtures de contenedor viven solo en
`tests/integration/conftest.py`. Un hook en `tests/conftest.py` aplica los marcadores
`unit`/`integration` según la ruta, así `pytest -m unit` y `just test-unit` no dependen de
Docker. Alternativa descartada: solo marcadores sobre la estructura plana - los marcadores
no evitan que `conftest.py` importe infraestructura, que es justo lo que rompe mutmut.

**Mutation testing solo sobre `domain/` y `application/`.** Son puros y sus tests son
instantáneos (206 mutantes en ~4 s); mutar adaptadores exigiría contenedores por mutante.
Herramienta: `mutmut` (la versión 3 soporta Python 3.12 y el layout `src/`). Corre en un
workflow programado y manual, no en cada push: es la señal más cara y cambia despacio. El
umbral se fija tras medir el resultado real (no se inventa un número antes).

**Los tests de propagación de campos son el arma contra los mutantes, no un relleno.** Cada
superviviente es "este campo no se comprueba". Se escribe una aserción por campo reenviado
(parametrizada, sobre un único conjunto de entradas) en lugar de decenas de tests
casi iguales.

**Property-based solo donde la propiedad es más clara que un ejemplo.** Invariantes de
`Change`/`Review` (campos preservados, estados coherentes), round-trip JSON de payloads de
eventos y la ley de idempotencia del repositorio (n ingestas con claves aleatorias dejan
exactamente tantos cambios como claves distintas). El resto de la lógica se prueba con
ejemplos explícitos, más legibles. Perfil `ci` de hypothesis: `derandomize=True` para que
un fallo sea reproducible y no intermitente.

**Tabla de decisión de `run_review` probando la activity directamente.** Es un método
`async` ordinario (no necesita el servidor de Temporal): ocho combinaciones de (agente
conocido, change existente, el agente lanza) con la precedencia explícita, p. ej. un agente
desconocido gana a un change inexistente. Rápido, sin contenedor, y cubre la rama que hoy
nunca se ejecuta.

**Transiciones de estado: solo las que existen.** `Change` solo tiene el estado `pending` y
`Review` es terminal. Se prueba lo real (los constructores producen siempre combinaciones
coherentes y las entidades son inmutables, así nadie puede "des-congelar" una review). La
máquina de estados de `Change` (`pending → reviewing → done/failed`) llega con
`finish_change` y se probará entonces; inventar transiciones ahora sería testear un
modelo que no existe.

**El esquema y los modelos se contrastan con `compare_metadata` de Alembic.** Las
migraciones se escriben a mano y los modelos aparte: es el sitio clásico donde derivan sin
avisar. Un test que ejecuta `upgrade head` y compara contra `Base.metadata` lo detecta; otro
verifica la reversibilidad `upgrade → downgrade → upgrade`. Si destapa diferencias
(p. ej. índices que existen en la migración pero no en el modelo) se corrigen aquí.

**Concurrencia con Postgres real, no con fakes.** El riesgo vive en la base de datos
(`ON CONFLICT` bajo carrera), así que un fake en memoria no demostraría nada. Se lanzan N
tareas `asyncio` con sesiones independientes sobre la misma clave natural y se comprueba
una fila, un evento y el mismo id devuelto.

**Recuperación = comportamiento observable de Temporal + idempotencia, sin matar procesos.**
(1) Worker de agentes ausente → el workflow queda en espera y termina cuando el worker
aparece. (2) Fallo transitorio de persistencia → la activity se reintenta y queda una
única review. (3) Acuse perdido tras confirmar: el repositorio de prueba persiste de
verdad y luego lanza una vez; el reintento vuelve a insertar y la clave única lo absorbe
(una review, un evento). Simular caídas reales de contenedor se descarta: lento, frágil y
no probaría más que (2) y (3).

**Cobertura: umbral global y otro más estricto para `domain/`+`application/`.**
`coverage.py` no admite umbrales por paquete, así que el global va en `pyproject.toml`
(`fail_under`) y el estricto en `coverage report --include=... --fail-under=...`
(justfile y CI). Se activa `--cov-branch`. Los números se fijan tras medir.

**Diferidos con motivo.** Contratos de API (schemathesis sobre el OpenAPI), autenticación y
autorización, seguridad de API (cabeceras, comparación en tiempo constante, inyección por
HTTP), E2E por HTTP y carga sobre `POST /ingest/commit`: todos requieren el endpoint, que
llega en `expose-commit-ingestion`. En lugar de dejarlo como intención vaga, este change
añade esas tareas a `tasks.md` de `expose-commit-ingestion`. Rendimiento hoy: el único
riesgo real (diff enorme) ya queda cubierto por el test de regresión de 5 MB a través del
workflow.

## Risks / Trade-offs

- [Riesgo] Mover ~15 ficheros de test puede romper imports y el historial de git →
  Mitigación: `git mv` en un único paso aislado y suite verde antes de añadir nada.
- [Riesgo] Mutantes equivalentes impiden llegar al 100 % → Mitigación: umbral realista y
  revisión manual de los supervivientes restantes, documentando los equivalentes.
- [Riesgo] Tests de concurrencia/recuperación intermitentes → Mitigación: se basan en
  invariantes finales (conteos en BD) y no en tiempos; el entorno de Temporal con salto de
  tiempo evita esperas reales.
- [Riesgo] El workflow de mutación puede romperse sin que nadie lo note, al no correr en
  cada push → Mitigación: ejecución semanal programada y `workflow_dispatch`; los pasos
  se prueban localmente con `just mutation` antes de fusionar.

## Open Questions

(ninguna - los umbrales numéricos se deciden con datos medidos durante `apply`)
