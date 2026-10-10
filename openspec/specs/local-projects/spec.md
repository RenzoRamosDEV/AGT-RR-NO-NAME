# local-projects Specification

## Purpose
TBD - created by archiving change add-local-projects-backend. Update Purpose after archive.

## Requirements

### Requirement: Activación por configuración
Los endpoints `POST /projects`, `DELETE /projects/{slug}` y `POST /projects/{slug}/sync-prs`
SHALL estar desactivados por defecto: con `LOCAL_PROJECTS_ENABLED` ausente o falsa SHALL
responder 404 a toda petición, con o sin token, sin tocar el disco ni la base de datos. Con
`LOCAL_PROJECTS_ENABLED=true` SHALL exigir la cabecera `X-Ingest-Token` válida (401 si falta o
es incorrecta) y contar contra el límite de peticiones.

#### Scenario: Función desactivada
- **WHEN** `LOCAL_PROJECTS_ENABLED` no está definida y se llama a `POST /projects` con un token válido
- **THEN** la respuesta es 404 y no se crea ningún proyecto ni se escribe ningún hook

#### Scenario: Sin token
- **WHEN** la función está activada y se llama a `POST /projects` sin `X-Ingest-Token`
- **THEN** la respuesta es 401 y no se crea nada

### Requirement: Alta de un proyecto desde una carpeta local
`POST /projects` con `{"path": "<ruta absoluta>"}` SHALL dar de alta el proyecto y responder 201 con
`id`, `slug`, `path`, `hooks_installed` (verdadero) y `github`. La ruta SHALL ser absoluta, sin
segmentos `..`, sin NUL, existente, no ser un enlace simbólico y ser exactamente la raíz de un
repositorio git; en otro caso SHALL responder 422 sin escribir nada. El slug SHALL ser `owner/repo`
cuando el remoto `origin` apunte a GitHub (URL https, `git@` o `ssh://`, con o sin `.git`) y
`github` verdadero; si no hay `origin` o no es de GitHub, SHALL ser el nombre de la carpeta y
`github` falso. Un slug o una ruta ya registrados SHALL dar 409. Si fallan los hooks, el proyecto
SHALL quedar sin registrar.

#### Scenario: Repo con origin de GitHub
- **WHEN** se da de alta una carpeta con `origin` `git@github.com:acme/widgets.git`
- **THEN** la respuesta es 201 con `slug` `acme/widgets` y `github` verdadero

#### Scenario: Repo sin remoto
- **WHEN** se da de alta la carpeta `/home/u/mi-repo` sin `origin`
- **THEN** el slug es `mi-repo` y `github` es falso

#### Scenario: Ruta que no es un repo
- **WHEN** se envía una ruta relativa, con `..`, con NUL, inexistente, un enlace simbólico, o una
  subcarpeta de un repo
- **THEN** la respuesta es 422 y no se crea ningún proyecto ni se escribe ningún hook

#### Scenario: Proyecto repetido
- **WHEN** se da de alta una ruta o un slug ya registrados
- **THEN** la respuesta es 409 y el proyecto existente no cambia

#### Scenario: Fallo al instalar los hooks
- **WHEN** la instalación de los hooks falla tras guardar el proyecto
- **THEN** la respuesta es un error y el proyecto no queda registrado

### Requirement: Hooks de git que informan de cada commit y push
Al dar de alta un proyecto el sistema SHALL instalar los hooks `post-commit` y `pre-push` en el
directorio de hooks efectivo del repo (respetando worktrees y `core.hooksPath` cuando apunta dentro
del repo). Si `core.hooksPath` apunta fuera del repo, o un hook existente no es un script de shell,
SHALL rechazar el alta con 422 sin modificar nada. Si ya existe un hook del usuario SHALL conservarlo
íntegro y añadir un bloque delimitado por `# >>> duelo >>>` y `# <<< duelo <<<`; instalar dos veces
SHALL dejar un único bloque, y reinstalar sobre un bloque anterior SHALL sustituirlo. El hook de
commit SHALL enviar `POST /ingest/commit` con el proyecto, la rama (`ref`), el sha, el título, el
autor y el diff del commit; el de push SHALL enviar los commits que se suben (como máximo los 20 más
recientes por referencia). Los hooks NUNCA SHALL bloquear ni retrasar de forma apreciable el commit
o el push: SHALL terminar con código 0, aunque la API esté caída o el token sea incorrecto, hacer el
envío en segundo plano con un plazo corto, no interpolar datos del commit en comandos de shell y no
restar la entrada estándar a los hooks posteriores.

El hook SHALL leer la URL de la API y el token **únicamente** del fichero de credenciales
(`hook.env`, modo 0600, en la ruta de `HOOK_ENV_PATH` o `~/.config/duelo/hook.env`) y NUNCA de
variables de entorno: `INGEST_URL` e `INGEST_TOKEN` del entorno de quien lanza git SHALL ignorarse.
El bloque instalado SHALL llevar la ruta de ese fichero (`--env-file`), de modo que una
`HOOK_ENV_PATH` personalizada funcione igual que la ruta por defecto. La URL SHALL ser `http` o
`https` con host; si no lo es, el hook SHALL no enviar nada. El token NUNCA SHALL escribirse en el
repo.

#### Scenario: Un commit aparece en el canal
- **WHEN** se hace un commit en un repo dado de alta y la API está activa
- **THEN** la API recibe un `POST /ingest/commit` con el sha, la rama, el título, el autor y el diff
  de ese commit

#### Scenario: API caída
- **WHEN** se hace un commit o un push con la API apagada
- **THEN** el comando de git termina con éxito y sin demora apreciable

#### Scenario: Hook previo del usuario
- **WHEN** el repo ya tenía un `post-commit` propio y se da de alta el proyecto
- **THEN** el hook conserva su contenido y además lleva un único bloque `duelo`, y sigue funcionando
  como antes

#### Scenario: hooksPath compartido
- **WHEN** `core.hooksPath` apunta a un directorio fuera del repo
- **THEN** el alta responde 422 y no se escribe ningún hook

#### Scenario: Push de varios commits
- **WHEN** se hace push de una rama con tres commits nuevos
- **THEN** la API recibe esos tres commits, y los ya enviados por `post-commit` no se duplican

#### Scenario: El entorno no redirige el envío
- **WHEN** se ejecuta `INGEST_URL=https://atacante git commit` en un repo con los hooks instalados
- **THEN** la API configurada recibe el commit y el host del atacante no recibe nada, ni el diff ni
  el token

#### Scenario: Ruta de credenciales personalizada
- **WHEN** la API corre con `HOOK_ENV_PATH` en una ruta distinta de `~/.config/duelo/hook.env` y se
  da de alta un proyecto
- **THEN** un `git commit` en ese repo llega a la API, porque el bloque instalado apunta a esa ruta

#### Scenario: URL no http
- **WHEN** el fichero de credenciales contiene `INGEST_URL=file:///etc/passwd` o una URL sin host
- **THEN** el hook no envía nada y el commit termina con éxito

### Requirement: Baja de un proyecto
`DELETE /projects/{slug}` SHALL quitar de los hooks el bloque `duelo` (dejando intacto el resto del
hook y borrando el fichero si solo contenía ese bloque) **antes** de eliminar el proyecto y, en
cascada, sus changes, reviews y eventos, y responder 204. Un slug inexistente SHALL dar 404. Si la
carpeta ya no existe, la baja SHALL completarse igualmente. Si los hooks no se pueden quitar (p. ej.
`.git/hooks` sin permiso de escritura), la API SHALL responder 409 con un mensaje accionable y
SHALL conservar el proyecto y su historial para poder repetir la baja.

#### Scenario: Baja con hook previo
- **WHEN** se da de baja un proyecto cuyo `post-commit` tenía contenido del usuario
- **THEN** el hook recupera exactamente su contenido original y el proyecto desaparece de `GET /projects`

#### Scenario: Slug inexistente
- **WHEN** se da de baja un proyecto que no existe
- **THEN** la respuesta es 404

#### Scenario: Los hooks no se pueden quitar
- **WHEN** la desinstalación de los hooks falla al dar de baja un proyecto
- **THEN** la respuesta es 409 con un `detail` que explica qué corregir, el proyecto y su historial
  siguen existiendo y los hooks no se han tocado en el resto de ficheros

#### Scenario: Carpeta desaparecida
- **WHEN** se da de baja un proyecto cuya carpeta ya no existe
- **THEN** la respuesta es 204 y el proyecto desaparece

### Requirement: Sincronización de PRs con gh
`POST /projects/{slug}/sync-prs` SHALL listar las PRs abiertas del proyecto con la CLI `gh` (sin
shell, con plazo) y registrar cada una como change de tipo `pr` con su diff, con la idempotencia
de la ingesta (mismo sha, mismo change), y responder 200 con `{"synced": n, "created": m}`, donde
`created` cuenta solo las nuevas. Un proyecto sin carpeta local SHALL dar 409, un slug inexistente
404, y `gh` ausente o sin sesión iniciada 503 con un mensaje que lo diga. Con
`PR_SYNC_INTERVAL_SECONDS` mayor que 0 el sistema SHALL repetir esa sincronización para todos los
proyectos locales con ese intervalo, y un fallo en uno SHALL no impedir los demás ni parar el
sincronizador; con 0 (por defecto) no SHALL haber sincronización periódica.

#### Scenario: PRs abiertas
- **WHEN** el repo tiene dos PRs abiertas y una ya estaba registrada
- **THEN** la respuesta es 200 con `synced` 2 y `created` 1

#### Scenario: gh no disponible
- **WHEN** `gh` no está instalado o no ha iniciado sesión
- **THEN** la respuesta es 503 con un mensaje que lo indica y no se crea ningún change

#### Scenario: Un proyecto falla en la sincronización periódica
- **WHEN** el sincronizador periódico falla en un proyecto
- **THEN** sigue con los demás y repite en el siguiente intervalo
