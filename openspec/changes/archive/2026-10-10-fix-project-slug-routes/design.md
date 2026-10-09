# Design

## Context

`react-router` no deja que `:slug` consuma una barra, así que `p/:slug` solo casa con slugs de un
segmento. El backend admite slugs con barra (`GET /projects/{slug:path}/changes`).

## Goals / Non-Goals

**Goals:** que `owner/repo` navegue y se muestre, sin romper los slugs de un segmento de los
mocks; que ninguna URL desconocida deje la página en blanco.

**Non-Goals:** cambiar el formato de la API, slugs con más de dos segmentos como caso soportado
de primera clase (funcionan, pero no se prueban más allá de uno), redirecciones de URLs antiguas.

## Decisions

- **Ruta única `p/*` + `parseProjectPath`.** Una ruta por forma (`p/:owner/:repo`) obligaría a
  duplicarla para los slugs sin barra de los mocks. Con el resto como cadena, `parseProjectPath`
  decide: con tres o más segmentos y `changes` en la penúltima posición es el detalle (slug = lo
  anterior, id = el último); en otro caso es el canal. Así un proyecto llamado `changes` o
  `x/changes` sigue siendo un canal.
- **Un helper para construir y otro para leer.** `projectPath(slug)` y `changePath(slug, id)`
  codifican cada segmento con `encodeURIComponent` y unen con `/`. Los componentes no arman URLs a
  mano.
- **Páginas con props.** `ChannelPage` y `ChangeDetailPage` reciben `slug` (y `id`) en lugar de
  leer `useParams`, y `ProjectRoute` es quien parsea. Los tests siguen entrando por `App`.
- **404 visible.** Una ruta `*` y las rutas `p/*` sin slug renderizan `NotFoundPage` dentro del
  `Shell`.
