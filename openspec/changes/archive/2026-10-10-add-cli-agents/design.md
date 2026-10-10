# Design

## Contexto

`ReviewAgent` (`application/ports.py`) ya es el puerto: `review(change) -> ReviewResult`. La activity
`run_review` carga el change, lanza latidos, llama al agente y guarda `Review(completed)` o, si el
agente lanza, `Review(failed)`. Solo hay un adaptador, `FakeAgent`. Este change añade dos adaptadores
reales sin tocar el workflow, los DTOs ni la API HTTP.

El worker `agents` ya está pensado para correr en la máquina del usuario, donde `claude` y `codex`
están autenticados. **No se usa ninguna clave de API**: los CLI se apoyan en esa sesión.

## Formato real observado de cada CLI (verificado ejecutándolos una vez con un diff de 5 líneas)

**Claude Code 2.1.296** — `claude -p --output-format json --json-schema <esquema> …` imprime UN objeto
JSON en stdout. Campos que importan: `is_error` (bool), `subtype` (`"success"`), `result` (texto con
el mismo JSON), `structured_output` (el objeto ya validado contra el esquema), `permission_denials`,
`total_cost_usd` (≈ 0,027 USD de lista por la review de prueba) y `terminal_reason`. Con
`--setting-sources ""` y `--strict-mcp-config` no carga hooks, MCP ni ajustes del usuario y sigue
usando la sesión iniciada. Tardó 5,5 s. Acepta el prompt por stdin.

**Codex 0.162.1** — `codex exec -s read-only --ephemeral --skip-git-repo-check --output-schema <f>
-o <salida> -C <dir> -` (el `-` lee el prompt de stdin). El fichero de `-o` contiene exactamente el
JSON del esquema (el último mensaje del agente) y stdout lo repite; stderr trae la transcripción y los
hooks del usuario. Tardó 8,3 s (~13 000 tokens).

Ambos devolvieron la misma forma `{summary, score, findings[{severity,file,line,message}]}` con el
esquema pedido.

**Solo lectura, comprobado con los CLI reales.** En un directorio con `hola.txt`, se pidió a cada CLI
(con exactamente los argumentos de este change) leer ese fichero y crear otro. Claude (`dontAsk` +
`Read,Grep,Glob`) leyó el contenido y respondió que «no tengo ninguna herramienta de escritura»;
Codex (`-s read-only`) leyó el contenido y respondió que «el sistema de archivos está en modo solo
lectura». Ninguno creó el fichero. Los dos aceptan el prompt por stdin (`claude -p` sin prompt
posicional, `codex exec -`). La ejecución completa de ambos agentes con un diff de 5 líneas pasa
(`tests/integration/agents/`, 16 s en total).

## Decisiones

**Prompt por stdin, no por argumento.** Un argumento de línea de comandos está limitado a ~128 KB en
Linux (60 000 caracteres UTF-8 pueden superarlo) y es visible para otros usuarios locales en
`/proc/<pid>/cmdline`: un diff puede contener secretos. Por stdin no hay límite práctico ni
exposición. Además, `--tools` de Claude es variádico y puede tragarse un prompt posicional. Se
verificó que ambos CLI lo aceptan. (La directiva original pedía «un solo argumento»; esto lo mejora.)

**Un runner, dos adaptadores.** `adapters/subprocess_runner.py` gana `input` (stdin), `exclude_env`
y `max_output_bytes`. Cada agente recibe el runner inyectado (por defecto `run_command`), de modo que
los tests no lanzan nada real. El runner ya crea un grupo de procesos propio y lo mata al vencer el
plazo; es asíncrono, así que los latidos de la activity siguen emitiéndose.

**Solo lectura.** Claude: `--tools Read,Grep,Glob`, `--permission-mode dontAsk`,
`--permission-prompts none`, `--strict-mcp-config`, `--disable-slash-commands`,
`--setting-sources ""`, `--no-session-persistence` y `--max-budget-usd` (tope contra bucles de
herramientas; configurable, 2 USD por defecto). No se usa `--bare` porque no lee la sesión OAuth.
Codex: `-s read-only --ephemeral`. Ningún argumento habilita escritura, ejecución ni red. Nota: Codex
ejecuta los hooks de usuario de su propia configuración; no hay un flag para desactivarlos y se
documenta.

**Prompt y prompt injection.** El título, el autor, la rama y el diff se tratan como datos no
confiables: van entre marcas con un identificador aleatorio por ejecución (`secrets.token_hex`), el
prompt ordena ignorar cualquier instrucción dentro de ellas y exige solo JSON. La defensa real es que
las herramientas son de solo lectura: lo peor que puede hacer un diff hostil es sesgar la review.
El diff se recorta a 60 000 caracteres con aviso explícito.

**Salida validada a mano.** Sin dependencia nueva: `parse_review_payload` comprueba tipos y rangos
(`score` entero 0-10 y no booleano, `severity` en la lista, `line` entero ≥ 0), acota a 50 hallazgos,
2 000 caracteres por mensaje y 4 000 de resumen, y guarda `file` vacío como «N/A» con `line` 0 (lo
mismo que `FakeAgent`). Claude: se usa `structured_output`, o `result` parseado si falta.

**Errores saneados.** Una jerarquía `CliAgentError(RuntimeError)` con mensajes FIJOS: CLI no
disponible, sesión no iniciada (se detecta por texto en salida/stderr y no se reintenta), plazo
vencido, error del CLI (solo el código de salida) y salida inválida. Nunca se vuelca stdout/stderr ni
rutas. La activity ya guarda `str(exc)` como `error` de la review fallida. Un fallo del agente no se
reintenta por Temporal (la activity lo captura), lo cual evita repetir un fallo de login.

**Plazo y concurrencia.** `AGENT_TIMEOUT_SECONDS` (240, validado `< 300` para quedar por debajo del
`start_to_close_timeout` de 5 min). Concurrencia: el worker de la queue `agents` fija
`max_concurrent_activities = AGENT_MAX_CONCURRENCY` cuando hay algún agente real, de modo que las
reviews sobrantes esperan EN LA COLA de Temporal (donde no consumen el plazo de la activity) y no
dentro de ella; además un semáforo compartido entre agentes (`AGENT_MAX_CONCURRENCY`) lo garantiza
si algún día se amplían los huecos. Con solo agentes de prueba no hay límite.

**Directorio de trabajo.** El agente recibe un `ProjectPaths` (puerto nuevo con
`path_of(project_id) -> str | None`, implementado por `SqlAlchemyProjectRepository`) y lo resuelve
él mismo: así `run_review` y los DTOs de Temporal no cambian (siguen viajando solo IDs). Si la ruta
existe y es un directorio, es el cwd; si no, un directorio temporal vacío (0700) que se borra.

**Entorno del hijo.** Hereda `HOME`, `PATH`, `XDG_*`, etc. para encontrar la sesión del usuario, pero
se le quitan `INGEST_TOKEN`, `OPERATOR_TOKEN`, `DATABASE_URL`, `ANTHROPIC_API_KEY` y
`OPENAI_API_KEY`. Las dos últimas, a propósito: con una clave en el entorno el CLI la usaría y
facturaría por API en lugar de la suscripción. Los ficheros temporales (esquema y salida de Codex) van
en un directorio `0700` propio con ficheros `0600` y se borran en `finally`.

**Registro por nombre.** `build_agents(names, config, project_paths)` en `adapters/agents/registry.py`:
`claude` → `ClaudeCliAgent`, `codex` → `CodexCliAgent`, resto → `FakeAgent`; sin distinguir
mayúsculas (la clave del diccionario conserva el nombre tal cual llega en `AGENT_NAMES`, que es el
que pide el workflow). El worker lo usa en lugar del diccionario de `FakeAgent`.

## Riesgos y límites

- **Consumo:** cada review gasta suscripción de Claude y de Codex (≈ 0,03 USD de lista y ~13 k tokens
  en el diff de prueba; más con diffs grandes o con contexto de repositorio). El límite de
  concurrencia y `--max-budget-usd` lo acotan.
- **Sin sesión:** el agente falla con un mensaje claro; la review queda `failed` y es reintentable.
- **Prompt injection:** mitigada por solo lectura, no eliminada: un diff puede sesgar la nota.
- **Hooks de Codex del usuario** se ejecutan dentro de cada review (no desactivables hoy).
- **Contexto de repositorio:** con proyecto local el agente puede leer ese repositorio (solo lectura),
  incluidos ficheros fuera del diff; es deliberado para dar contexto.
- **Calidad:** la nota y los hallazgos dependen del modelo; no se verifican contra el código.
