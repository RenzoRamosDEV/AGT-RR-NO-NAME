# Duelo · frontend

React 19 + Vite + TypeScript. `pnpm dev` arranca el servidor de desarrollo, `pnpm build` genera
`dist/`, `pnpm preview` lo sirve, `pnpm test` ejecuta Vitest y `pnpm lint` pasa Biome.

## PWA

El build de producción es instalable (manifiesto web) y su interfaz abre sin conexión: un service
worker generado por `vite-plugin-pwa` (Workbox) precachea el *app shell* del build. Los datos de
la API nunca se cachean; sin red se ven los estados de error habituales.

- **Instalar.** Sirve `dist/` y usa «Instalar aplicación» del navegador (icono en la barra de
  direcciones en Chrome/Edge; «Añadir a pantalla de inicio» en móvil).
- **HTTPS requerido.** Fuera de `localhost` el navegador solo registra el service worker sobre
  HTTPS; el repositorio no despliega el frontend, así que eso corresponde a quien lo sirva.
- **En desarrollo no hay service worker.** `pnpm dev` y los tests no lo registran. Si has abierto
  antes un `pnpm preview` en el mismo origen y ves código viejo, bórralo en DevTools → Application
  → Service Workers → «Unregister» (o «Clear site data»).
- **Actualizaciones.** Con una versión nueva aparece el aviso «Nueva versión disponible»; la
  página no se recarga hasta pulsar «Actualizar» (`src/components/UpdatePrompt.tsx`).
- **Iconos.** `public/pwa-192x192.png`, `public/pwa-512x512.png` y
  `public/pwa-maskable-512x512.png` se generaron con ImageMagick desde
  `src/assets/brand/mark-dark-128.png` (el *maskable* lleva el emblema al 80 % sobre `#0d1117`).
  Al salir de un original de 128 px, el de 512 queda algo blando; con el logo original a mayor
  resolución se pueden regenerar con los mismos comandos:

  ```sh
  magick mark.png -filter Lanczos -resize 512x512 public/pwa-512x512.png
  magick -size 512x512 xc:'#0d1117' \( mark.png -resize 410x410 \) -gravity center -composite \
    public/pwa-maskable-512x512.png
  ```
