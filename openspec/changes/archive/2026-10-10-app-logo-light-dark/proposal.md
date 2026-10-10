# Proposal

## Why

La marca de Duelo es un SVG genérico de dos espadas cruzadas que no tiene nada que ver con el
producto. El usuario aporta dos logos propios, uno pensado para el modo oscuro (emblema neón de
burbujas de chat con el centro blanco y `<>`) y otro para el claro (el mismo icono en 3D
acristalado, con el centro oscuro y `<>` cian), y pide usarlos en la app según el tema.

## What Changes

- La marca de la barra superior pasa a ser el emblema del logo del tema en vigor, junto al texto
  «Duelo». Sale una versión compacta del logo (solo el emblema central, recortado) porque la
  composición completa, con las burbujas sueltas, es ilegible a 28 px.
- Los estados vacíos (sin proyectos, canal vacío) y la página 404 usan la composición completa del
  logo del tema en vigor como imagen principal, con el efecto de carga `img-fx` cuando hay WebGL.
  Sustituye a las dos ilustraciones anteriores.
- El logo cambia solo al cambiar el tema, sin parpadeo y desde la primera pintura, tanto con el
  selector Sistema/Claro/Oscuro como con el esquema de color del sistema.
- El favicon pasa a ser el emblema, con una versión por esquema de color del sistema, y se añade el
  icono de Apple. Se retira el favicon SVG de las espadas.
- Los assets se generan a partir de los originales: recorte del padding transparente, tamaños para
  interfaz y WebP para las imágenes grandes.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: marca de la aplicación con logo por tema.

## Impact

- `frontend/src`: componente `BrandLogo` (sustituye a `Logo`), `layout/Shell.tsx`, `App.tsx`,
  `features/channel/ChannelPage.tsx`, `components/fx/HeroImage.tsx` y sus tests, `index.css`.
- `frontend/src/assets/brand/` (logos y héroes) y `frontend/public/` (favicons y icono de Apple);
  se eliminan `favicon.svg`, `hero-duelo.png` y `hero-review.png`.
- `docs/adr/0006-logo-por-tema.md`.
- Sin cambios en el backend ni en la API.
