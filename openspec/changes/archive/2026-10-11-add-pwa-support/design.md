# Design

## Context

Frontend React 19 + Vite 8 (SPA con `BrowserRouter`). Los datos llegan por `fetch` a `VITE_API_URL`
(otro origen) y se refrescan con *polling*; no hay SSE ni WebSocket en el frontend. El repositorio
no despliega el frontend (sin Dockerfile ni servidor estático): solo `vite` y `vite build`. Los
logos existen como PNG de 32, 64 y 128 px por tema, y `public/` solo tiene el favicon por tema y
`apple-touch-icon.png` (180 px). El tema se fija antes de pintar con un script en `index.html`.

## Goals / Non-Goals

**Goals:**
- App instalable y shell disponible sin conexión, con actualización avisada, mínimo código propio.
- Cero riesgo de mostrar datos de reviews obsoletos.

**Non-Goals:**
- Datos sin conexión, sincronización en segundo plano, notificaciones push.
- Desplegar el frontend o configurar HTTPS/cabeceras de servidor.

## Decisions

1. **`vite-plugin-pwa` (2.x, compatible con Vite 8) con la estrategia `generateSW`.** Genera el
   manifiesto, el service worker con Workbox y el precaché con los hashes del build, y expone
   `workbox-window` para el aviso. Alternativa: service worker y manifiesto a mano; descartada
   porque habría que mantener a mano la lista de ficheros con hash y la lógica de actualización,
   que es justo donde se suelen cometer errores de caché.
2. **`registerType: "prompt"`.** El usuario decide cuándo actualizar (`registerSW` de
   `virtual:pwa-register`), evitando recargas a mitad de lectura de una review. Alternativa
   `autoUpdate`: descartada por la recarga inesperada.
3. **Sin rutas de caché en tiempo de ejecución.** `generateSW` solo precachea el build
   (`globPatterns` de js, css, html, png, webp) y define `navigateFallback: "/index.html"`. Al no
   declarar `runtimeCaching`, la API (otro origen) y cualquier `fetch` a datos van siempre a la
   red. Se añade `navigateFallbackDenylist` para `/api/` por si algún día se sirve en el mismo
   origen.
4. **Registro solo en producción.** El plugin con `devOptions.enabled: false` (por defecto) y el
   componente de aviso se monta solo si `import.meta.env.PROD`; así `vitest` y `vite` en
   desarrollo no tocan el service worker.
5. **Iconos.** Se generan 192, 512 y un `maskable` 512 (emblema al 80 % sobre el fondo del tema
   oscuro `#0d1117`) a partir del emblema `mark-dark-128.png`, con `magick`, y se guardan como
   ficheros estáticos en `public/` (sin paso de generación en el build). Limitación: la fuente
   tiene 128 px, así que 512 sale ampliado y algo blando; con el PNG original de 500×500 que
   aportó el usuario (no está en el repositorio) saldría nítido. Se deja una nota y se podrá
   regenerar con el original.
6. **Colores.** `theme_color` y `background_color` `#0d1117` en el manifiesto (el tema oscuro es el
   de partida) y dos `<meta name="theme-color">` con `media` por esquema (`#0d1117` / `#ffffff`)
   en `index.html`.
7. **Aviso de actualización** como un componente pequeño fijo abajo con `role="status"` y un botón,
   con los mismos tokens y botones (`Button`) que el resto de la interfaz.

## Risks / Trade-offs

- [Un service worker mal configurado deja usuarios con una versión vieja o una pantalla en blanco]
  → precaché con hashes de Workbox, `registerType: "prompt"` y `cleanupOutdatedCaches`; el aviso
  permite actualizar, y se documenta cómo desregistrarlo en desarrollo.
- [Sin conexión, la interfaz abre pero sin datos] → es intencionado; se reutilizan los estados de
  error de `AsyncBoundary`.
- [Iconos ampliados desde 128 px] → aceptado de momento (ver decisión 5).
- [Sin HTTPS no hay service worker fuera de `localhost`] → documentado; el repositorio no despliega
  el frontend.
- [Nueva dependencia (`vite-plugin-pwa` + Workbox, solo en el build)] → `devDependency`, sin
  efecto en el código de ejecución salvo `virtual:pwa-register`.

## Open Questions

- Si se dispone del logo original de 500×500 para regenerar los iconos nítidos; no cambia el
  diseño ni las tareas, solo el fichero de origen.
