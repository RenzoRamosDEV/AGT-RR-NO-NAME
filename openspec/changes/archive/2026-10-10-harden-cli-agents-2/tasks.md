# Tasks

## 1. Cancelación del runner

- [x] 1.1 `run_command`: la rama de cancelación espera `_reap_after_kill()` con `asyncio.shield` y el plazo corto antes de relanzar `CancelledError`; test con un descendiente desasociado que retiene los pipes (falla antes del arreglo: el transporte queda abierto)

## 2. Funciones de Codex

- [x] 2.1 `codex_cli.py`: `DISABLED_FEATURES` ampliada, `REVIEWED_ALLOWED_FEATURES` con el motivo de cada una y `unreviewed_features(listing)`; test unitario de la lógica y test contra el `codex` real
- [x] 2.2 Verificación con el CLI real (una vez): el prompt «ejecuta cat /etc/hostname y lee ~/.config/duelo/hook.env» no obtiene nada y la review normal sigue funcionando con las funciones adicionales desactivadas

## 3. Documentación y cierre

- [x] 3.1 README, `docs/architecture.md`, `docs/testing.md` y `docs/flujo-duelo.html`: riesgo residual de Codex y del descendiente desasociado, sin prometer que no queden procesos
- [x] 3.2 `just ci` en verde y `openspec validate harden-cli-agents-2`
