# Design

## Context

Repositorio vacío hoy (ni siquiera tiene `git init` hasta este change). No hay dominio,
no hay Temporal, no hay base de datos. Esta fase solo monta el esqueleto sobre el que
las fases siguientes (dominio, workflows, agentes, frontend, PRs/chat, evaluación)
construirán, siguiendo la arquitectura hexagonal y el stack fijados en
`openspec/config.yaml`. Ver `proposal.md - Por qué` para la motivación.

## Goals / Non-Goals

**Goals:**
- Un `just dev` reproducible levanta Postgres + Temporal + Temporal UI + API en Docker.
- La API arranca como paquete Python hexagonal vacío (carpetas `domain/`, `application/`,
  `adapters/`, `workflows/`, `entrypoints/` presentes aunque casi sin contenido) con
  `import-linter` ya validando la regla de dependencias desde el primer commit.
- CI en verde en una PR vacía: lint, tipos, build.
- Un ADR registrando la decisión Temporal vs. alternativas, para referencia futura.

**Non-Goals:**
- No se implementa ningún caso de uso de dominio real (`Change`, `Review`, etc.) todavía.
- No se define el esquema de Postgres ni Alembic; Postgres se levanta en Docker Compose
  pero la API no lo usa todavía (ni siquiera para `/health`).
- No hay workflows de Temporal reales, solo el servicio de Temporal disponible en
  Docker Compose para fases futuras.
- No se monta el frontend con features; solo un placeholder de Vite que compila.

## Decisions

**Monorepo con `backend/` y `frontend/` como carpetas hermanas, no paquetes separados
con versionado propio.** Un solo repo, un solo CI, coherente con que es un proyecto
personal de portafolio sin publicación a registries. Alternativa descartada: repos
separados (añade fricción sin beneficio a este tamaño).

**`import-linter` configurado ya en Fase 0, aunque los paquetes estén casi vacíos.**
Fijar la regla de dependencias (`domain <- application <- adapters/entrypoints/workflows`)
desde el primer commit evita que el primer código de dominio (Fase 1) ya nazca violándola.
Alternativa descartada: añadirlo en Fase 1 - se descarta porque es exactamente el tipo de
disciplina que se diluye si se pospone.

**`GET /health` sin dependencias, en vez de esperar a tener Postgres conectado.**
El criterio de "hecho" de la Fase 0 es explícito: `just dev` levanta todo y CI pasa. Un
`/health` que ya comprobara Postgres acoplaría esta fase a trabajo de Fase 1 (modelo de
datos). Se deja `/ready` (con comprobación de Postgres/Temporal) para cuando esas piezas
existan, como requirement MODIFIED sobre esta misma capacidad `service-health`.

**ADR 0001 se escribe ahora, no al final del proyecto.** El spec general ya contiene el
análisis completo (Temporal vs DBOS/Hatchet/Inngest/Prefect); este change solo lo traslada
a `docs/adr/0001-temporal-vs-alternativas.md` en el formato de ADR del repo, como registro
de decisión arquitectónica citable. No se reabre el análisis aquí.

**Docker Compose con perfiles `infra` y `app`, sin el worker `agents`.** El worker
`agents` nunca corre en Docker (necesita los CLIs de Claude Code y Codex logueados en la
máquina del usuario) - ver restricción dura en `openspec/config.yaml`. En esta fase ese
worker ni siquiera existe como proceso, así que no hay nada que excluir activamente, pero
el `docker-compose.yml` se estructura ya con perfiles para que añadir `agents` por error
en Docker sea una decisión explícita y visible, no un descuido.

## Risks / Trade-offs

- [Riesgo] Configurar `import-linter` sobre paquetes casi vacíos puede parecer trabajo
  prematuro → Mitigación: el coste es bajo (unas pocas líneas de config) y el beneficio
  (no violar la regla desde el commit 1) es alto; se documenta la regla en el ADR si hace
  falta más contexto en el futuro.
- [Riesgo] Sin tests de dominio todavía, la pirámide de tests de la Fase 2 en adelante no
  tiene nada que validar en esta fase → Mitigación: esta fase solo necesita un test mínimo
  de `GET /health` (smoke test) para que el pipeline de CI tenga algo real que ejecutar,
  no una suite completa.
- [Riesgo] Nombrar el ADR "0001" fija un número que debe mantenerse consistente en
  fases futuras → Mitigación: se documenta la convención (`docs/adr/{número}-{slug}.md`,
  incremental) en el propio ADR para que las fases siguientes la seder.

## Migration Plan

No aplica (greenfield, no hay sistema previo que migrar). El "despliegue" de esta fase es
el primer merge a la rama principal; no hay rollback más allá de revertir el commit.
