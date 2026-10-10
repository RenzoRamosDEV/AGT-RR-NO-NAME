# Tasks

## 1. Espera acotada y salida truncada (runner)

- [x] 1.1 `run_command`: plazo corto de recolección tras `killpg`, cierre de pipes si no termina y `CommandResult.truncated`; test con un descendiente desasociado que reproduce el cuelgue (falla antes del arreglo) y test de salida recortada

## 2. Plazo con margen

- [x] 2.1 `application/review_timeouts.py` con las constantes; el workflow y `config.py` las usan; `AGENT_TIMEOUT_SECONDS` ≤ plazo de la activity − 30 s; tests de configuración

## 3. Claude y Codex

- [x] 3.1 Claude: `--restricted` en los argumentos y test; una salida truncada es `CliBadOutput`
- [x] 3.2 Codex: `--ignore-user-config`, `--ignore-rules` y las funciones desactivadas; directorio temporal vacío siempre; tamaño del fichero de salida comprobado antes de leerlo; tests
- [x] 3.3 Verificación con los CLI reales (una vez): los tests con `RUN_CLI_AGENT_TESTS=1` incluyen la petición de leer/ejecutar fuera del directorio y comprueban que no hay fuga

## 4. Documentación y cierre

- [x] 4.1 README, `docs/architecture.md`, `docs/testing.md` y `docs/flujo-duelo.html`: Codex solo diff, riesgo residual, máximo de `AGENT_TIMEOUT_SECONDS`
- [x] 4.2 `just ci` en verde y `openspec validate harden-cli-agents`
