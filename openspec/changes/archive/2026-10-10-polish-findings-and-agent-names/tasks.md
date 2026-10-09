# Tasks

## 1. Hallazgos sin ubicación

- [x] 1.1 `findingFile` y `findingLine` en `lib/findings.ts` y grupo «Sin archivo» al final, con tests unitarios (`N/A`, vacío, línea 0, orden de grupos y de severidad)
- [x] 1.2 Panel y cards usan los helpers; verificar con test de render

## 2. Agentes desconocidos

- [x] 2.1 `AgentName` pasa a `string`, se elimina `toAgent`; avatar de iniciales; tests unitarios y de la API (regresión: `agent_1` ya no es «Claude»)

## 3. Cierre

- [x] 3.1 `pnpm lint`, `tsc -b`, `pnpm build`, `pnpm test` en verde
