# Design

## Decisiones

**Puertos (en `application/ports.py`) y adaptadores.** `GitRepository` (inspecciona una ruta y
devuelve raíz y URL de `origin`), `HookInstaller` (instala y desinstala los hooks), `GithubPrSource`
(PRs abiertas con su diff) y `ProjectCatalog` (alta y baja de proyectos locales). Las excepciones
(`InvalidRepository`, `HookInstallError`, `GithubUnavailable`, `ProjectAlreadyExists`) viven junto a
los puertos, como `ReviewStartError`. Los adaptadores usan un único ejecutor de subprocesos
(`adapters/subprocess_runner.py`): `asyncio.create_subprocess_exec` con lista de argumentos (nunca
shell), plazo y `kill` al vencer, y entorno con `GIT_TERMINAL_PROMPT=0`.

**Slug.** Función pura en `domain/project.py` (`slug_for_repository`): si `origin` es de GitHub
(`https://github.com/o/r(.git)`, `git@github.com:o/r(.git)`, `ssh://git@github.com/o/r(.git)`)
es `o/r` y `github=True`; si no, el nombre de la carpeta con `github=False`. Cada segmento se
valida con `[A-Za-z0-9._-]+` (sin `.` ni `..`); un nombre que no cumpla es un 422.

**Persistencia.** Tres columnas en `projects`: `path` (texto, único, nulo), `hooks_installed` y
`github` (booleanos, `false` por defecto). `Project` gana esos campos con valores por defecto, así
que los proyectos antiguos y los tests existentes no cambian. El borrado se apoya en las FK
`ON DELETE CASCADE` ya existentes (changes, reviews vía changes, events).

**Orden del alta.** Validar la ruta → insertar el proyecto (aquí salta el 409 por slug o ruta
duplicados, antes de tocar el disco) → instalar los hooks → si fallan, borrar el proyecto
(compensación) y devolver el error. Así un fallo no deja un proyecto sin hooks ni hooks con el slug
de otro.

**Validación de la ruta.** Absoluta, sin NUL, sin segmentos `..`, el último componente no es un
enlace simbólico, es un directorio, y `git rev-parse --show-toplevel` coincide con su `realpath`
(es la raíz y no una subcarpeta). `--absolute-git-dir` y `--git-common-dir` dan los directorios
reales de git (worktrees incluidos).

**Dónde se instalan los hooks.** `git rev-parse --path-format=absolute --git-path hooks` respeta
`core.hooksPath` y worktrees. Si el resultado cae fuera de la raíz del repo y de su `git-common-dir`
(típicamente un `core.hooksPath` global compartido por todos los repos) se rechaza con 422: un
bloque ahí se ejecutaría en repos ajenos con el slug de este.

**Bloque en el hook.** Se inserta justo después del shebang (no al final: un `exit` previo del
usuario lo dejaría sin ejecutar) entre `# >>> duelo >>>` y `# <<< duelo <<<`. Si el hook existente
no es un script de shell (`sh`, `bash`, `dash`, `zsh`) se rechaza con 422 en vez de corromperlo.
Instalar es idempotente (reemplaza el bloque anterior) y desinstalar quita solo el bloque; si el
fichero queda vacío (solo shebang) y lo creó Duelo, se borra. La detección de «lo creó Duelo» es
que el fichero, sin el bloque, sea solo el shebang que escribimos.

**Qué ejecuta el hook.** El bloque llama a `"<python del backend>" -m duelo.entrypoints.hook
<evento> --project '<slug>' "$@"`, con ruta y slug entre comillas simples escapadas; los datos del
commit nunca pasan por el shell: el módulo (solo biblioteca estándar) los lee con `git` en
subprocesos de lista y manda el JSON con `urllib`. El módulo lee `INGEST_URL` e `INGEST_TOKEN` del
entorno o de `~/.config/duelo/hook.env` (el instalador lo crea con modo 0600 en un directorio 0700
y lo reescribe en cada alta).

**No bloquear.** El módulo hace `os.fork()`: el padre sale con 0 de inmediato y el hijo se separa
(`setsid`), envía con plazo de 5 s y se calla ante cualquier error. Sin `fork` (Windows) envía en
el propio proceso con plazo de 2 s. Coste medio: el arranque de Python (decenas de ms).

**pre-push y la entrada estándar.** Git entrega las referencias por stdin. Si nuestro bloque
(que va el primero) las consumiera, un `pre-push` posterior del usuario no las vería. El bloque las
vuelca a un fichero temporal, se las pasa al módulo con `--stdin-file` y rehace stdin con `exec <`
antes de borrar el temporal. Por cada referencia a subir (se ignoran los borrados) se envían como
máximo 20 commits: `remote..local`, o, si el remoto no la tiene, `local --not --remotes=<remoto>`.

**Diff del hook.** Se corta en 1 000 000 de caracteres; el servidor lo vuelve a acotar con
`MAX_DIFF_CHARS` y marca `diff_truncated`, como cualquier ingesta.

**PRs con gh.** `GithubPrSource` ejecuta `gh pr list --state open --limit 30 --json
number,title,author,headRefName,headRefOid,url,updatedAt` y `gh pr diff <n>` en la carpeta del
proyecto. `gh` ausente, sin sesión o con salida inválida es `GithubUnavailable` (503). La
sincronización llama al mismo caso de uso de ingesta de PRs, así que la idempotencia es la de
siempre (proyecto, tipo, sha).

**Sincronizador periódico.** `ApiDependencies.background_jobs` lista tareas que el `lifespan` de
la app arranca con `asyncio.create_task` y cancela al cerrar. `periodic()` (en
`entrypoints/api/background.py`) repite el trabajo cada `PR_SYNC_INTERVAL_SECONDS`, captura y loguea
cualquier excepción y acepta un `sleep` inyectable para los tests. Solo se registra si el
intervalo es mayor que 0 y la función está activa.

**Activación.** `LOCAL_PROJECTS_ENABLED=false` (defecto) hace que los tres endpoints respondan 404
antes de mirar el token (no delatan que existen), igual que `OPERATOR_TOKEN` ausente. Con la
función activa, la composición construye los adaptadores; apagada, las dependencias quedan en
`None` y ni siquiera se importan subprocesos.

**`INGEST_URL`.** Por defecto `http://127.0.0.1:8000` (el backend no sabe en qué puerto lo lanzó
uvicorn). Quien use otro puerto fija `INGEST_URL`.

**CORS.** Se añade `DELETE` a los métodos permitidos.

## Riesgos y límites

- **Escritura en `.git/hooks` con un token.** Quien tenga `INGEST_TOKEN` puede hacer que la API
  escriba hooks (código que se ejecuta en cada commit) en cualquier repo legible por el usuario que
  la corre. Mitigaciones: apagado por defecto, solo con la API en la máquina del usuario, 404
  indistinguible cuando está apagada, rate limit, solo rutas que son la raíz de un repo, nada de
  `core.hooksPath` externo y bloque acotado y desinstalable. No hay que activarlo en un servidor
  compartido ni tras un proxy público.
- **Git sobre repos no confiables.** Los comandos son de lectura y se ejecutan sin shell; aun así
  git puede leer la configuración del repo. La ruta la elige quien tiene el token, que ya es de
  confianza para esto.
- **Token en disco.** `hook.env` (0600) contiene el token de ingesta; es el mismo secreto que ya
  viaja por el entorno de la API.
- **Multi-proceso.** El sincronizador periódico es por proceso: con varios workers de uvicorn cada
  uno lo ejecutaría (inocuo por la idempotencia, pero redundante).
- **Windows.** Sin `fork` el hook envía en el propio proceso con plazo de 2 s; no se prueba aquí.
- **Los hooks no se ejecutan con `--no-verify`** (y `post-commit` sí): quien salte `pre-push` solo
  pierde los commits que no pasaron antes por `post-commit`.
- **Reintentos de PRs.** Una PR actualizada tiene un sha nuevo y, por tanto, un change nuevo; es
  el comportamiento de la ingesta de PRs ya existente.
