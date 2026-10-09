# Design

## Context

El backend envía findings con `file` y `line` obligatorios, pero un agente puede no saber la
ubicación y rellena `N/A` y `0` (el `FakeAgent` lo hace). La API también envía el agente como
texto libre.

## Goals / Non-Goals

**Goals:** no mostrar datos de ubicación inventados; no atribuir a Claude lo que hizo otro agente.

**Non-Goals:** cambiar el contrato del backend (que `file` y `line` sean opcionales) ni el color o
icono por agente.

## Decisions

- **Normalizar al leer, en `lib/findings.ts`.** `findingFile` devuelve `undefined` si el archivo
  está vacío o es `N/A` (sin distinguir mayúsculas) y `findingLine` si la línea no es un entero
  positivo; el panel y las cards usan solo esos helpers.
- **«Sin archivo» al final.** Los grupos con archivo van por orden alfabético; el grupo sin
  archivo siempre último, para no tapar los hallazgos localizados. La severidad se sigue
  ordenando igual dentro de cada grupo y los hallazgos sin línea van tras los que la tienen.
- **`AgentName` pasa a `string`.** `toAgent` desaparece: `Review.agent` es el nombre tal cual.
  `agentLabel` pone mayúscula inicial a cualquier nombre y `AgentAvatar` muestra sus iniciales
  (una o dos letras; `agent_1` → `A1`), manteniendo «Claude» y «Codex» como casos conocidos.
  Estadísticas ya usaba `agentLabel`, así que no cambia.

## Risks / Trade-offs

- Un agente real llamado `N/A` perdería su ubicación en pantalla; es un riesgo asumido porque
  es el marcador que usa el propio backend.
