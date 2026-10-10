## MODIFIED Requirements

### Requirement: Barrido de alcanzabilidad de los commits
Con `LOCAL_PROJECTS_ENABLED`, la API SHALL ejecutar cada `REACHABILITY_SWEEP_INTERVAL_SECONDS`
segundos (15 por defecto; 0 lo apaga) un barrido que, por cada proyecto con carpeta local, consulta a
git los commits alcanzables desde todas las referencias y desde `HEAD` (como máximo
`REACHABILITY_WINDOW_COMMITS`, 5000 por defecto) con una única llamada sin shell y con plazo. Los
changes de tipo `commit` del proyecto cuyo SHA no esté en ese conjunto SHALL marcarse como
deshechos (`discarded_at`), y los marcados cuyo SHA vuelva a estar SHALL desmarcarse. Si el conjunto
está truncado por la ventana, solo se evaluarán los changes creados desde la fecha del commit más
antiguo de la ventana y cada candidato a deshecho SHALL confirmarse con una comprobación individual
antes de marcarse. Antes de CADA consulta a git, el sistema SHALL revalidar que la carpeta
registrada no es un enlace simbólico y que es la raíz de su propio repositorio (`.git` propio); si
no, SHALL tratarlo como un error de git. Git SHALL ejecutarse sin configuración de sistema ni de
usuario y con `core.fsmonitor` y `core.hooksPath` desactivados. Un error de git en un proyecto
(carpeta movida, borrada o sustituida, plazo, git ausente) SHALL registrarse y NO marcar nada en ese
proyecto, y los demás proyectos SHALL seguir. Un SHA solo SHALL llegar a un argumento de git si es
hexadecimal de 7 a 64 caracteres.

#### Scenario: Commit deshecho con reset
- **WHEN** se hace `git reset --hard HEAD~1` en el repositorio del proyecto y corre el barrido
- **THEN** el change de ese commit pasa a `commit_state = discarded` y se emite `commit.discarded`

#### Scenario: Commit deshecho con amend
- **WHEN** se hace `git commit --amend` y corre el barrido
- **THEN** el change del commit antiguo queda deshecho y el del nuevo SHA sigue activo

#### Scenario: Commit recuperado
- **WHEN** un commit marcado como deshecho vuelve a ser alcanzable y corre el barrido
- **THEN** el change se desmarca (`active`) y se emite `commit.restored`

#### Scenario: Error de git
- **WHEN** la carpeta del proyecto ya no existe o git falla
- **THEN** no se marca ningún change de ese proyecto y el barrido sigue con los demás

#### Scenario: Carpeta sustituida por un enlace a otro repositorio
- **WHEN** la carpeta registrada se sustituye por un enlace simbólico a otro repositorio
- **THEN** no se consulta ese repositorio y no se marca ningún change del proyecto

#### Scenario: Carpeta que ya no es la raíz de su repositorio
- **WHEN** la ruta registrada es una subcarpeta de un repositorio, o su `.git` apunta a otro
- **THEN** el barrido lo trata como un error de git y no marca nada

#### Scenario: Proyecto sin carpeta y PRs
- **WHEN** un proyecto no tiene carpeta local, o el change es de tipo `pr`
- **THEN** el barrido no lo evalúa nunca

### Requirement: Detección de commits revertidos al ingerir
Al ingerir un commit, el sistema SHALL reconocer un `git revert` solo por el formato que genera
Git: título que empieza por `Revert "` o `Reapply "` y, en el cuerpo, una línea EXACTA
`This reverts commit <sha>.` con el SHA completo en minúsculas hexadecimales (40 o 64 caracteres);
cualquier otra mención (en un párrafo, en el título, SHA corto, mayúsculas, sin punto final) SHALL
ignorarse. Es lo que declara el mensaje: no se valida que el parche sea el inverso. Si el SHA es
distinto del suyo, SHALL guardarse en el propio commit (`reverts_sha`). Un commit de tipo `commit` SHALL estar revertido mientras exista en el MISMO
proyecto un commit de revert que siga en la rama (no deshecho) con ese SHA, llegue antes o después
que el original. Si el original existe cuando nace el revert, SHALL emitirse `commit.reverted` una
sola vez (una reingesta no lo repite). Si el commit original no existe en el sistema, SHALL NOT
ocurrir ningún error. El `body` SHALL NOT guardarse.

#### Scenario: Revert de un commit conocido
- **WHEN** se ingiere un commit con el mensaje de `git revert` y el original ya existe
- **THEN** el original pasa a `commit_state = reverted` con `reverted_by` apuntando al nuevo

#### Scenario: Mención suelta
- **WHEN** un commit que no es un `git revert` (título distinto o frase dentro de un párrafo) cita
  `This reverts commit <sha>`
- **THEN** no se marca nada

#### Scenario: SHA que no es completo y en minúsculas
- **WHEN** el mensaje trae un SHA corto o en mayúsculas
- **THEN** no se marca nada

#### Scenario: Revert de un commit desconocido
- **WHEN** el SHA revertido no existe en el proyecto
- **THEN** la ingesta termina bien y no se marca nada

#### Scenario: El revert llega antes que el original
- **WHEN** se ingiere un commit de revert y después el commit que revierte
- **THEN** el original aparece revertido en cuanto existe

#### Scenario: Reenvío del revert
- **WHEN** se reingiere el mismo commit de revert
- **THEN** no se duplica el evento ni cambia la marca

#### Scenario: Revert deshecho
- **WHEN** el commit de revert se deshace (`git reset`) y corre el barrido
- **THEN** el original vuelve a `commit_state = active` y `reverted_by = null`, y si el revert
  vuelve a ser alcanzable el original vuelve a estar revertido

#### Scenario: Revert corregido con amend
- **WHEN** el commit de revert se corrige con `git commit --amend` y se ingiere el nuevo SHA
- **THEN** el original pasa a estar revertido por el nuevo commit y se emite otro `commit.reverted`

#### Scenario: Revert que sigue en la rama
- **WHEN** otro commit dice revertir un original que ya está revertido por un commit que sigue en la rama
- **THEN** la marca no cambia
