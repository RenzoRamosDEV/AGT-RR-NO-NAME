# Tasks

## 1. Iconos y metadatos

- [x] 1.1 Generar `public/pwa-192x192.png`, `public/pwa-512x512.png` y `public/pwa-maskable-512x512.png` desde `src/assets/brand/mark-dark-128.png` con `magick` (maskable: emblema al 80 % sobre `#0d1117`). Verificación: `file` muestra los tamaños 192/512/512 y se abren sin recortar el emblema.
- [x] 1.2 En `index.html`, añadir los dos `theme-color` por esquema de color. Verificación: `pnpm build` y el HTML de `dist/` los contiene junto al enlace al manifiesto.

## 2. Plugin y service worker

- [x] 2.1 Añadir `vite-plugin-pwa` como `devDependency` y configurarlo en `vite.config.ts` (manifiesto con nombre, nombre corto, `lang: "es"`, `display: "standalone"`, colores, iconos; `registerType: "prompt"`; precaché de js/css/html/png/webp; `navigateFallback` a `/index.html` con `navigateFallbackDenylist` para `/api/`; `cleanupOutdatedCaches`; sin `runtimeCaching`). Verificación: `pnpm build` genera `manifest.webmanifest` y `sw.js`, y el `sw.js` no contiene rutas de datos.
- [x] 2.2 Comprobar que la configuración de `vitest` no se ve afectada (el plugin no corre en test). Verificación: `pnpm exec tsc -b` y `pnpm lint` en limpio.

## 3. Aviso de actualización

- [x] 3.1 Crear el componente `UpdatePrompt` (con `useRegisterSW` de `virtual:pwa-register/react`, `role="status"`, botones «Actualizar» y «Cerrar», operable con teclado) y montarlo en `App` solo en producción; añadir el tipo `vite-plugin-pwa/react` a `tsconfig`. Verificación: `pnpm exec tsc -b` sin errores y revisión visual con `vite preview`.

## 4. Comprobación

- [x] 4.1 Servir el build con `vite preview` y comprobar en el navegador (Chromium headless o DevTools): manifiesto detectado, service worker activo, recarga de `/stats` sin conexión, y que las peticiones a la API no pasan por el service worker. Verificación: capturas o salida de la comprobación en el informe final.
- [x] 4.2 Dejar una nota breve en `frontend/README.md` (instalar, HTTPS requerido, cómo borrar el service worker en desarrollo, origen de los iconos). Verificación: el README la incluye.

## Workflow follow-up

- Archivar el change (`openspec archive`) y commit/PR cuando el usuario lo pida.
