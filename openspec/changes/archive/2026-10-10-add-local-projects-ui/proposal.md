# Proposal

## Why

Hoy un proyecto solo existe si alguien hace un `insert` en la base de datos, y los commits solo
llegan si se envían a mano con `curl`. El objetivo es que el usuario añada un repositorio de su
disco desde la propia interfaz, lo elija en la barra lateral y vea aparecer cada commit, push o PR
sin recargar. El backend (change paralelo) ofrece `POST /projects` con una ruta local, instala los
hooks de git y sincroniza PRs con `gh`; este change es la parte de interfaz.

## What Changes

- Botón «Añadir proyecto» (barra lateral y estado vacío) que abre un diálogo accesible con un
  campo de ruta absoluta, el aviso de que se instalarán hooks de git (`post-commit`, `pre-push`) y
  errores claros por código (404, 409, 422, 401). El token de ingesta se pide en un campo de
  contraseña y vive solo en memoria. Tras añadir, el proyecto aparece en la barra lateral y se
  selecciona.
- Ajustes lista los proyectos con su ruta y el estado de los hooks, permite «Sincronizar PRs»
  (solo si el repo está en GitHub) y «Quitar proyecto», con una confirmación explícita que avisa de
  que borra su historial.
- Auto-actualización: la barra lateral, el canal y el detalle se refrescan solos cada ~5 s, en
  silencio y pausados con la pestaña oculta, sin perder filtros, búsqueda, «cargar más» ni
  posición de scroll, y con un indicador discreto «Actualizado hace N s».
- El cliente de la API gana `addProject`, `removeProject` y `syncPrs`; el modo de ejemplo
  (sin `VITE_API_URL`) los simula en memoria con las mismas reglas de error.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: alta y baja de proyectos locales, sincronización de PRs y auto-actualización.

## Impact

- `frontend/src`: `lib/api.ts`, `data/source.tsx`, `lib/useAsync.ts`, `layout/Shell.tsx`,
  `features/channel/*`, `features/review/ChangeDetailPage.tsx`, `features/settings/*`, nuevos
  `components/Modal.tsx`, `features/projects/*`, `lib/polling.tsx`, `lib/liveness.ts`,
  `lib/localPath.ts`, estilos y tests.
- Sin dependencias nuevas y sin cambios de backend (el contrato lo implementa otro change).
