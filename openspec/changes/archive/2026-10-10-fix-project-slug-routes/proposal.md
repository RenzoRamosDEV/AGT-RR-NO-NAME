# Proposal

## Why

Los slugs reales del backend tienen la forma `owner/repo` (por ejemplo `acme/widgets`), pero las
rutas de la interfaz eran `p/:slug` y `p/:slug/changes/:id`, y un parámetro de ruta no casa con una
barra. Con la API real, `/` redirigía a `/p/acme/widgets`, que no coincidía con ninguna ruta, y
la página quedaba en blanco. Los mocks usaban slugs sin barra, por eso ningún test lo detectó.

## What Changes

- Una sola ruta `p/*` cuyo resto se interpreta con un helper único (`lib/projectPath.ts`):
  `/p/<slug>` es el canal y `/p/<slug>/changes/<id>` es el detalle, con el slug de uno o más
  segmentos.
- Todos los enlaces (barra lateral, redirección de `/`, tarjetas del canal, migas del detalle) se
  construyen con el mismo helper, que codifica cada segmento.
- Una ruta comodín muestra una página «No encontrado» en lugar de dejar la página en blanco.
- Los mocks incluyen un proyecto con slug `owner/repo` y hay un test de regresión.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: la navegación admite slugs `owner/repo` y las rutas desconocidas muestran una
  página «No encontrado».

## Impact

- `frontend/src`: `App.tsx`, `lib/projectPath.ts` (nuevo), `layout/Shell.tsx`,
  `features/channel/ChannelPage.tsx`, `features/review/ChangeDetailPage.tsx`, `data/mock.ts` y
  tests.
- Sin dependencias nuevas y sin cambios de backend.
