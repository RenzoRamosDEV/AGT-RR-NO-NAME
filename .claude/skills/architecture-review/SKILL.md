---
name: architecture-review
description: Revisa la arquitectura de un cambio - separación de responsabilidades, regla de dependencias entre capas, acoplamiento, cohesión, dependencias circulares, SOLID y puertos y adaptadores. Úsalo al añadir módulos, mover código, crear puertos/adaptadores o cuando pidan "revisa la arquitectura", "¿respeta las capas?".
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(uv run lint-imports:*), Bash(uv run mypy:*)
---

# Revisión de arquitectura

Juzga contra la arquitectura **declarada del proyecto** (`openspec/config.yaml`,
`docs/architecture.md`, `docs/adr/`), no contra una preferencia genérica. Si el diff se
desvía de lo declarado, la pregunta es "¿hay un ADR que lo justifique?", no "¿me gusta?".

## 1. Comprobación determinista primero

`cd backend && uv run lint-imports` (contrato "Hexagonal layering"). Si falla, es
`BLOQUEANTE` `CONFIRMADO` con la salida del comando como evidencia. Que pase no basta: mira
también lo que el contrato no ve (abajo).

## 2. Regla de dependencias de este repo

```
domain  <-  application  <-  adapters | entrypoints | workflows
```

- `domain/` no importa nada del proyecto salvo `domain/`; sin frameworks (ni FastAPI, ni
  SQLAlchemy, ni Temporal, ni Pydantic de API).
- `application/` define casos de uso y **puertos** (`Protocol`); depende solo de `domain/`.
- `adapters/`, `entrypoints/` y `workflows/` son capas **hermanas**: ninguna importa a otra.
  Si una necesita algo de otra, el contrato compartido sube a `application/` (así se movió
  `ReviewCommitInput`) o se inyecta una fábrica.
- Solo la raíz de composición (`composition.py`, `worker.py`) conoce las tres capas a la
  vez; no debe acumular lógica de negocio.

## 3. Lo que `import-linter` no ve

- **Fugas de infraestructura por tipos:** un `AsyncSession`, un `Client` de Temporal o un
  modelo ORM en la firma de un caso de uso o de una entidad.
- **Lógica de negocio en el borde:** reglas (límites, recortes, decisiones) dentro de un
  router, un adaptador o una activity en vez de en `domain/`/`application/`. Se prueba y
  se muta mejor ahí.
- **Anemia o dominio acoplado al esquema:** entidades que son un espejo de la tabla.
- **Puertos que filtran el adaptador:** excepciones o tipos específicos del driver que
  cruzan el puerto (el adaptador debe traducirlos a errores del puerto).
- **Puertos diseñados por adelantado:** el repo crea un puerto cuando un change lo necesita,
  no antes. Una abstracción con una sola implementación y sin segundo consumidor es
  candidata a sobra (ver `safe-refactoring`).

## 4. Principios (úsalos como lente, no como dogma)

- **Responsabilidad única:** ¿se puede describir el módulo sin "y"?
- **Abierto/cerrado e inversión de dependencias:** ¿añadir un agente nuevo exige tocar el
  núcleo o solo registrar un adaptador?
- **Segregación de interfaces:** puertos pequeños (`ChangeRepository(add, get)`), no
  repositorios todoterreno.
- **Cohesión y acoplamiento:** cambios que obligan a editar muchos módulos a la vez;
  módulos que se importan en círculo (aunque sea con imports locales para evitarlo).
- **Dirección de las dependencias en tests:** `tests/unit/domain` y `tests/unit/application`
  no deben importar adapters (rompe el aislamiento de mutmut).

## 5. Decisiones arquitectónicas

Un cambio que contradice una decisión vinculante (hexagonal, Temporal con IDs y no diffs,
outbox transaccional, cliente TS generado desde OpenAPI, agentes en la máquina del usuario)
y no trae ADR es `IMPORTANTE`. Si la decisión nueva es razonable, la salida correcta es
pedir el ADR, no rechazar el cambio.

## Salida

Cada hallazgo indica la regla incumplida, el import o la firma exacta (`ruta:línea`), el
coste concreto (qué se vuelve imposible de probar o de cambiar) y la corrección mínima
(mover, inyectar, extraer puerto).
