# Proposal

## Why

La revisión de Codex sobre `add-cli-agents` (PR #6) señaló cinco problemas. Se han comprobado uno a
uno en el código y con los CLI reales:

1. **Claude sin `--restricted`.** Los argumentos limitaban las herramientas a `Read,Grep,Glob`, pero
   no confinaban las de fichero al directorio de trabajo. Comprobado con el CLI real: con
   `--permission-mode dontAsk` ya se denegaba leer `/etc/hostname`, pero eso depende del modo de
   permisos; `--restricted` lo confina de forma dura y deja de depender de él.
2. **Codex ejecuta comandos.** `-s read-only` impide escribir, pero el modelo puede **ejecutar
   comandos de shell de lectura y leer fuera del repositorio**. Comprobado: con los argumentos
   anteriores, un prompt «ejecuta `cat /etc/hostname`» devolvió el contenido (`Renzo`).
3. **Cuelgue tras el plazo.** `run_command` mata el grupo de procesos al vencer el plazo y luego
   espera `communicate()` sin otro plazo: un nieto con `start_new_session=True` que heredó el stdout
   mantiene el pipe abierto y cuelga la llamada hasta que él termine.
4. **Salida truncada leída como completa.** `run_command` recorta stdout/stderr a un máximo sin
   avisar, y el agente de Codex lee el fichero de `-o` con un recorte silencioso: una respuesta
   cortada se parsea como si estuviera entera.
5. **Sin margen entre el plazo del agente y el de la activity.** `AGENT_TIMEOUT_SECONDS` admitía hasta
   299,9 s con una activity de 300 s: al vencer el CLI no queda tiempo para limpiar y persistir la
   `Review(failed)`.

## What Changes

- Claude se lanza además con `--restricted` (se mantienen `--strict-mcp-config`,
  `--disable-slash-commands` y `--setting-sources ""`).
- Codex se lanza con `--ignore-user-config`, `--ignore-rules` y con las herramientas que ejecutan
  comandos o salen del directorio desactivadas (`--disable shell_tool`, `unified_exec`, `hooks` y las
  de navegador, aplicaciones, plugins e imágenes). Sin herramienta de shell Codex no puede leer el
  repositorio, así que revisa **solo el diff** y trabaja siempre en un directorio temporal vacío.
- `run_command` tiene un plazo corto de recolección tras matar el proceso; si los pipes no se cierran
  los libera y abandona la espera. `CommandResult` indica `truncated`.
- Los agentes rechazan (fallo controlado) una salida truncada en lugar de parsearla.
- `AGENT_TIMEOUT_SECONDS` admite como máximo el plazo de la activity menos 30 s, derivado de una
  constante común.

## Capabilities

### New Capabilities

### Modified Capabilities
- `cli-review-agents`: «Solo lectura», «Salida estructurada validada», «Plazo y concurrencia
  limitados» y «Directorio de trabajo del agente» cambian; nuevo requisito «Espera acotada tras el
  plazo».

## Impact

- Código: `adapters/agents/claude_cli.py`, `adapters/agents/codex_cli.py`, `adapters/agents/cli_common.py`,
  `adapters/subprocess_runner.py`, `config.py`, `workflows/review_change.py` y un módulo nuevo
  `application/review_timeouts.py` con las constantes de plazo.
- Comportamiento visible: el agente de Codex ya no lee el repositorio del proyecto (solo el diff); el
  máximo de `AGENT_TIMEOUT_SECONDS` baja de 300 a 270.
- Documentación: README, `docs/architecture.md`, `docs/testing.md` y `docs/flujo-duelo.html`.
