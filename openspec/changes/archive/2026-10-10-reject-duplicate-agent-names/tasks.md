# Tasks

## 1. Configuración

- [x] 1.1 `Settings.agent_names` rechaza nombres repetidos (sin distinguir mayúsculas) con un mensaje que nombra el duplicado, y conserva el orden y la escritura; tests de configuración (repetido, repetido por mayúsculas, lista válida)

## 2. Dominio

- [x] 2.1 `reviews_to_reuse` no reutiliza con una lista de agentes con repetidos; test de dominio que falla antes del arreglo

## 3. Documentación y cierre

- [x] 3.1 Nota en el `design.md` de `reuse-commit-reviews-for-prs` y en el README sobre crear el índice con `CONCURRENTLY` en una base grande
- [x] 3.2 `just ci` en verde y `openspec validate`
