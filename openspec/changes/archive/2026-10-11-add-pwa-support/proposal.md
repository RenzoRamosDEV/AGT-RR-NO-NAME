# Proposal

## Why

Duelo se usa a diario para vigilar repos y ver las reviews de los agentes. Poder instalarlo como
una aplicación (ventana propia, icono en el escritorio o el móvil) y que su interfaz abra al
instante, incluso sin red, lo hace más cómodo sin cambiar el producto.

## What Changes

- Manifiesto web (`manifest.webmanifest`) con nombre, colores del tema, `display: standalone`,
  idioma `es` e iconos de 192 y 512 px, más uno `maskable`.
- Service worker que precachea el *app shell* (HTML, JS, CSS, logos y fuentes del build) para que
  la interfaz abra sin conexión, con navegación a `index.html` para las rutas de la SPA.
- La API y los datos NUNCA se cachean: las peticiones a la API siempre van a la red y, sin
  conexión, la interfaz muestra sus estados de error existentes en lugar de datos viejos.
- Aviso de «nueva versión disponible» con un botón para recargar, en vez de actualizar a
  escondidas a mitad de una lectura.
- Registro del service worker solo en el build de producción; en desarrollo (`vite`) no se
  registra, para no cachear código en vivo.
- Metadatos en `index.html` (`theme-color` por tema, enlace al manifiesto).

## Capabilities

### New Capabilities
- `pwa-install`: instalación de la aplicación, interfaz disponible sin conexión, y política de
  caché que excluye los datos de la API.

### Modified Capabilities

## Impact

- `frontend/package.json` (dependencia de desarrollo `vite-plugin-pwa`; trae `workbox-build` y
  `workbox-window`), `frontend/vite.config.ts`, `frontend/index.html`, `frontend/public/` (iconos),
  `frontend/src/main.tsx` y un componente nuevo para el aviso de actualización.
- No cambia el backend ni la API. No hay despliegue del frontend en el repositorio (solo
  `vite`/`vite build`), así que el requisito de HTTPS para el service worker se documenta pero no
  se configura aquí.
- Los tests existentes de frontend no se ven afectados por el registro (no corre en `vitest`).
