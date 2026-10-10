# Design

## Context

El backend (change paralelo) expone, con `X-Ingest-Token`: `POST /projects {path}` → 201
`{id, slug, path, hooks_installed, github}` (404 función desactivada, 409 ya existe, 422 no es un
repo git, 401 token), `DELETE /projects/{slug}` → 204 y `POST /projects/{slug}/sync-prs` →
`{synced, created}` (503 si falta `gh`). `GET /projects` añade `path`, `hooks_installed` y
`github`. El navegador no puede dar rutas reales de disco, así que la ruta se escribe o se pega.

## Goals / Non-Goals

**Goals:** alta/baja de proyectos desde la UI, sincronizar PRs y ver los cambios nuevos sin
recargar, sin parpadeos ni pérdida de estado de la página.

**Non-Goals:** explorador de carpetas, autenticación de lectura, SSE o WebSockets (el outbox con SSE
sigue previsto para más adelante; el sondeo cada ~5 s es el mecanismo de esta fase) y cambios de
backend.

## Decisions

- **Sondeo en `useAsync`, no en cada pantalla.** `useAsync(load, { pollMs, pollWhile, equals })`
  repite `load` en silencio: no pasa por `loading`, conserva los datos ante un fallo
  (`refreshFailed`), no solapa peticiones, ignora respuestas de una `load` anterior, se pausa con
  `document.visibilityState === "hidden"` y refresca de inmediato al volver a ser visible. `equals`
  mantiene la misma referencia si el resultado no cambió, así que no hay re-render ni parpadeo.
  `refresh()` fuerza una recarga silenciosa (la usan el alta y la baja).
- **Intervalo inyectable.** `PollingProvider` da el periodo (`main.tsx` usa 5000 ms); sin
  proveedor el sondeo está desactivado, de modo que los tests existentes no cambian y los nuevos
  eligen su propio intervalo con temporizadores falsos.
- **El canal no pierde «cargar más».** Las páginas extra se asocian a la clave de la consulta
  (`slug`, tipo, estado, búsqueda), no a la identidad de la primera página. Los elementos ya
  mostrados que la primera página refrescada deja de cubrir (porque llegó uno nuevo y se desplazó)
  se conservan tras ella, de modo que no se pierde ni se duplica ninguno.
- **Detalle: sondeo mientras la review no ha terminado.** `pollWhile` solo sigue mientras el estado
  agregado es `pending` o `running`; un change terminado no se consulta más.
- **Proyectos en un contexto de la `Shell`.** Una única carga compartida (barra lateral, Ajustes,
  redirección de `/`) con `refresh`, y `openAddProject` para abrir el diálogo desde cualquier
  sitio. Así añadir o quitar un proyecto se refleja a la vez en todas partes.
- **Diálogo propio sobre `<dialog>`.** `Modal` usa el elemento nativo (`showModal` si existe, `open`
  como alternativa), `aria-modal`, `aria-labelledby`, foco inicial en `[data-autofocus]`, Tab
  cíclico, Escape que cierra y devolución del foco al elemento que lo abrió.
- **Token solo en memoria.** Se reutiliza `lib/ingestToken` (campo de contraseña, nunca en storage
  ni en la URL); un 401 lo olvida.
- **Mensajes por código.** `request` lee `detail` cuando la respuesta de error lo trae como texto
  (el 503 de `sync-prs` explica qué falta) y mantiene «El servidor respondió N.» en otro caso; la
  UI traduce 404/409/422/401 con textos propios. Las respuestas 204 no se parsean.
- **Modo de ejemplo coherente.** `createMockSource` simula alta, baja y sincronización con las
  mismas reglas de error (401 sin token, 422 ruta no absoluta, 409 duplicado, 503 sin GitHub), en
  memoria por instancia.

## Risks / Trade-offs

- Sondeo cada 5 s por pestaña abierta: aceptable en local y con un usuario; SSE lo sustituirá.
- Con el cursor de desplazamiento del modo de ejemplo, un elemento nuevo puede desplazar la
  paginación; la unión de lo ya mostrado lo evita en la lista visible.
- «Quitar proyecto» borra el historial en el servidor: por eso exige una confirmación explícita
  con el foco inicial en «Cancelar».
