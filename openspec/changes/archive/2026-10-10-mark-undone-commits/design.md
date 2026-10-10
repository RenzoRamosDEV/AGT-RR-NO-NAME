# Design

## Vocabulario

- **COMMIT DESHECHO** («Ya no está en la rama»): el SHA ya no es alcanzable desde ninguna ref ni
  desde `HEAD`. Cubre `reset`, `commit --amend`, `rebase` y borrar la rama.
- **COMMIT REVERTIDO** («Revertido por `<sha corto>`»): hay un commit posterior que lo invierte con
  `git revert`. El commit original SIGUE en la rama (por eso no es «deshecho»).
- Precedencia: deshecho gana a revertido. Una PR nunca está deshecha ni revertida (`commit_state` es
  siempre `active`): el estado solo se calcula para `kind = commit`.

## Deshecho: barrido de alcanzabilidad

Git no avisa cuando se pierde un commit (no hay hook para `reset` ni para `--amend`), así que se
pregunta periódicamente. La tarea la arranca la API en el mismo sitio que la sincronización de PRs
(`background_jobs`), solo con `LOCAL_PROJECTS_ENABLED`, cada `REACHABILITY_SWEEP_INTERVAL_SECONDS`
(15 por defecto; 0 = apagado).

Por cada proyecto con carpeta local, UNA llamada al repo, sin shell y con plazo:
`git -C <ruta> log --all --max-count=N --format=%H %ct`. `--all` incluye todas las refs y `HEAD`, así
que un commit en cabeza desacoplada o en medio de un rebase sigue contando como alcanzable.

### Ventana (`REACHABILITY_WINDOW_COMMITS`, 5000)

- Si git devuelve menos de N commits el conjunto está **completo**: se evalúan todos los changes de
  tipo commit del proyecto. La pertenencia al conjunto es concluyente.
- Si devuelve exactamente N está **truncado** (repo grande): hay commits alcanzables que no aparecen.
  Solo se evalúan los changes creados desde la fecha del commit más antiguo de la ventana (los más
  antiguos pueden ser alcanzables aunque no estén), y a cada candidato a «deshecho» se le hace una
  comprobación individual (`git for-each-ref --contains <sha>` y `git merge-base --is-ancestor <sha>
  HEAD`) antes de marcarlo, para no marcar uno que se ingirió tarde (recuperado por `pre-push`) y es
  anterior a la ventana. Quitar la marca solo exige que el SHA esté en el conjunto.
- El SHA solo llega a un argumento de git tras validarse como hexadecimal de 7 a 64 caracteres (los
  SHAs guardados vienen de la ingesta y pueden ser cualquier texto: nunca deben poder ser una
  opción de git).

### Garantías

- Un error de git (repo movido o borrado, plazo, git ausente) se registra y NO marca nada en ese
  proyecto; los demás siguen.
- Si un change marcado vuelve a ser alcanzable (`git reset` de vuelta, restauración desde el
  reflog) se desmarca (`discarded_at = NULL`) y se emite `commit.restored`.
- Idempotente: marcar solo toca los changes cuyo estado cambia y emite el evento una vez.
- **Límite documentado**: un commit ingerido con un SHA que nunca existió en ese repositorio (una
  prueba manual con `POST /ingest/commit`) aparecerá como deshecho en un proyecto local. Los
  proyectos sin carpeta local y los changes de tipo `pr` no se evalúan nunca. Los SHAs guardados
  abreviados o en mayúsculas se comparan en minúsculas y solo por igualdad exacta con el SHA completo.

## Revertido: al ingerir

El hook envía solo la primera línea del mensaje como `title`, y un `git revert` escribe el SHA en el
cuerpo (`This reverts commit <sha40>.`). Se añade un campo opcional `body` (cuerpo del mensaje,
acotado) al hook y a la petición de ingesta. Los hooks antiguos no lo envían y todo sigue igual.

Al ingerir un commit, `parse_reverted_sha(title, body)` extrae el SHA de `This reverts commit <sha>`
y ese SHA se guarda **en el propio commit de revert** (`changes.reverts_sha`). El estado «revertido»
del original no se guarda: se **deriva** al leer. Un commit está revertido mientras exista un commit
de revert **vivo** (del mismo proyecto, tipo commit, no deshecho y con `reverts_sha` = su SHA); el más
reciente es el que se muestra en `reverted_by`. El `body` no se guarda.

Se descartó un puntero en el original (`reverted_by_change_id`) porque depende del orden en que
ocurren las cosas: la API ingiere un `--amend` del revert al instante, pero el barrido tarda hasta
15 s en ver que el revert antiguo se perdió, así que el nuevo no podía sustituirlo y el original
acababa mal marcado. Con el dato en el revert:

- da igual el orden de llegada (el revert puede llegar antes que el original);
- **un revert deshecho ya no revierte**: si se hace `reset` del revert, el original vuelve a
  `active` y `reverted_by` a `null`, y si el revert vuelve, vuelve a estar revertido;
- un `git commit --amend` del revert deja otro SHA con el mismo mensaje: el original pasa a estar
  revertido por el nuevo, llegue antes el nuevo commit o la marca del antiguo;
- no hay carreras ni coordinación entre ingestas simultáneas.

Si el original ya existe cuando nace el commit de revert, el repositorio anota `commit.reverted` en la
línea de tiempo del original, en la misma transacción y una sola vez (una reingesta no lo repite). El
estado no depende de ese evento.

## Datos

Migración tras `g7d5e9b3c126`: `changes.discarded_at timestamptz NULL` y
`changes.reverts_sha varchar(64) NULL`, con un índice parcial `(project_id, reverts_sha) WHERE
reverts_sha IS NOT NULL` (solo los commits de revert, muy pocos, entran en él). Con downgrade.
Ninguna review ni change se borra o modifica salvo esas dos columnas, y los changes existentes
quedan sin marca (`active`).

## API

`commit_state` ∈ {`active`, `discarded`, `reverted`} y `reverted_by` (`{id, head_sha}` o `null`) en
cada elemento del canal y en el detalle: campos aditivos. El listado resuelve el revert vivo con un
`LATERAL` dentro de la misma consulta (mismo patrón que los contadores de reviews, sin consultas
extra por fila); el detalle lo pide con `ChangeRepository.live_reverter`. `commit_state` no cambia
`review_status` ni los contadores de revisión de la interfaz.

## Eventos

`commit.discarded`, `commit.restored` (payload: `change_id`, `project_id`) y `commit.reverted`
(además, `reverted_by_change_id`), en la misma transacción que el hecho que los causa, y en la lista
blanca de eventos que expone `GET /changes/{id}/events`.

## Interfaz

Estilo GitHub/Slack actual, con los tokens `--warning` y `--warning-bg` (ya cumplen AA en los dos
temas). La fila lleva un borde izquierdo ámbar, fondo tintado, icono de «deshacer» con texto
alternativo y, en el centro, la etiqueta en mayúsculas con su subtítulo (sin depender solo del
color). El título sigue legible (tachado sutil opcional). En la vista compacta la etiqueta queda en
la misma línea. El detalle muestra un aviso ámbar con el mismo texto y un enlace al change del
revert si existe. La cabecera de la lista añade «N deshechos» (cuenta lo cargado). Con
`prefers-reduced-motion` no hay transiciones nuevas.

## Riesgos

- El barrido consume algo de CPU y un proceso `git` por proyecto y tick. Con 5000 commits tarda del
  orden de decenas de milisegundos; el intervalo y la ventana son configurables y 0 lo apaga.
- Varios workers de uvicorn ejecutarían el barrido cada uno: inocuo por idempotencia.
- Una PR con el mismo SHA que un commit deshecho no se marca (solo los commits).
