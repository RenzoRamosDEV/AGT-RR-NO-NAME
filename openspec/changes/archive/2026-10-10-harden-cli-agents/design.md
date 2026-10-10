# Design

## Verificación previa con los CLI reales (una ejecución por variante)

Se pidió a cada CLI leer o ejecutar algo **fuera** de su directorio de trabajo (`/etc/hostname`,
cuyo contenido, `Renzo`, se conoce de antemano para detectar fugas):

| Variante | Resultado |
|---|---|
| Claude, argumentos de `add-cli-agents` (`dontAsk`) | Denegado (`permission_denials` lo registra): no leyó el fichero |
| Claude + `--restricted` | Denegado, con el mensaje «`/etc/hostname` is outside … `--restricted` confines the file tools to the working directory» |
| Codex, argumentos de `add-cli-agents` | **Ejecutó `cat /etc/hostname` y devolvió `Renzo`**: el sandbox `read-only` no impide leer |
| Codex + `--ignore-user-config --ignore-rules --disable shell_tool --disable unified_exec --disable hooks` | «No puedo ejecutar comandos de shell con las herramientas disponibles en esta sesión»: sin fuga y sin comando en la transcripción |

Conclusiones: el punto 2 (Codex) era un riesgo real; el punto 1 (Claude) no era explotable con
`dontAsk` en la prueba, pero `--restricted` lo convierte en un confinamiento duro que no depende del
modo de permisos, y es coherente con la defensa en profundidad.

## Decisiones

**Claude.** Se añade `--restricted` a los argumentos existentes. Según `claude --help` quita las
herramientas que ejecutan código y `WebFetch`, ignora los ajustes de usuario/proyecto/locales y confina
las herramientas de fichero a los directorios de trabajo. Con él sigue valiendo el uso de la carpeta
del proyecto como directorio de trabajo (se puede leer el repositorio, y solo él).

**Codex.** Se añaden `--ignore-user-config` (no carga `$CODEX_HOME/config.toml`; la sesión sigue en
`CODEX_HOME`, verificado: el agente sigue autenticado) y `--ignore-rules`, y se desactivan con
`--disable <feature>` (equivale a `-c features.<nombre>=false`) las funciones que ejecutan comandos o
salen del directorio. Los nombres son los reales de `codex features list`: `shell_tool`,
`unified_exec`, `hooks`, `view_image`, `apps`, `plugins`, `browser_use`, `browser_use_external`,
`browser_use_full_cdp_access`, `computer_use`, `in_app_browser` e `image_generation`. Quitar
`hooks` además evita que corran los hooks del usuario dentro de la review (el riesgo que antes solo se
documentaba). La red ya está cerrada por el sandbox `read-only`.

**Consecuencia: Codex revisa solo el diff.** Sin la herramienta de shell Codex no tiene forma de leer
ficheros, así que ya no sirve darle la carpeta del proyecto: trabaja siempre en un directorio temporal
vacío (menos superficie, no se expone el repositorio). Claude conserva el contexto del repositorio.
`CliAgent` gana un atributo `uses_project_folder` (verdadero para Claude, falso para Codex).

**Riesgo residual de Codex.** La lista de funciones es una lista de denegación: una versión futura de
Codex con una herramienta nueva que lea el sistema de ficheros no estaría desactivada. Mitigaciones:
sandbox `read-only` (sin escritura ni red), directorio de trabajo temporal vacío, entorno sin secretos
de Duelo ni claves de API, prompt que trata el diff como dato no confiable, y los tests de
integración con los CLI reales (`RUN_CLI_AGENT_TESTS=1`) que comprueban que un prompt que pide
ejecutar un comando no obtiene su salida. No se cambia `HOME`: perdería la sesión iniciada.

**Espera acotada tras el plazo (`run_command`).** `communicate()` se lanza como tarea. Al vencer el
plazo: `killpg`, y se espera esa tarea con `KILL_GRACE_SECONDS` (2 s). Si no termina porque un
descendiente en otra sesión conserva el pipe, se cancela, se cierra el transporte del proceso (libera
los descriptores) y se lanza `CommandTimeout` igualmente. El descendiente desasociado sigue vivo (no
hay forma fiable de localizarlo desde fuera); se documenta, y el agente ya no queda colgado. El código
accede a `process._transport` (privado de asyncio) porque no hay API pública para cerrar los pipes de
un `Process`; está aislado en una función y cubierto por un test que reproduce el cuelgue.

**Salida truncada.** `CommandResult.truncated` es verdadero si stdout o stderr superaron
`max_output_bytes`. Claude: una salida truncada es `CliBadOutput`. Codex: se comprueba el tamaño del
fichero de `-o` ANTES de leerlo y, si supera el límite, `CliBadOutput`; lo truncado de stderr/stdout
no se parsea (solo se mira su cola para detectar la sesión no iniciada).

**Margen de plazo.** Nuevo `application/review_timeouts.py` con `RUN_REVIEW_START_TO_CLOSE` (5 min),
`AGENT_TIMEOUT_MARGIN` (30 s) y `MAX_AGENT_TIMEOUT_SECONDS` (= diferencia, 270). Lo importan el
workflow y la configuración, de modo que no pueden desincronizarse; `AGENT_TIMEOUT_SECONDS` admite como
máximo ese valor (inclusive). El margen cubre: matar el grupo, la espera de recolección (2 s), borrar
los temporales y persistir la review fallida.

## Riesgos

- Codex pierde el contexto del repositorio: las reviews de Codex son solo sobre el diff.
- Un descendiente desasociado de un CLI puede sobrevivir al plazo (se abandona, no se mata).
- El nombre de las funciones de Codex puede cambiar entre versiones: un nombre desconocido no rompe la
  ejecución pero dejaría la función activa; el test con el CLI real lo detecta.
