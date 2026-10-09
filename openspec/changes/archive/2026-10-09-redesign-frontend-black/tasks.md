# Tasks

## 1. Base y sistema de diseño

- [x] 1.1 Instalar `react-router`, `border-beam`, `thinking-orbs` y verificar `pnpm build` y `pnpm lint` en verde
- [x] 1.2 Crear tokens CSS negros, tipografía y estilos globales; verificar que con `prefers-color-scheme: light` el fondo sigue negro (test de render)
- [x] 1.3 Componentes UI base (botón, badge, tarjeta, avatar de agente) con tests de render y contraste AA de los tokens

## 2. Layout y navegación

- [x] 2.1 Shell con barra lateral y rutas `/p/:slug`, `/stats`, `/settings`; verificar navegación y destino activo con test
- [x] 2.2 Accesibilidad de teclado y foco visible; verificar recorrido con Tab en test

## 3. Canal y reviews

- [x] 3.1 Canal con mensajes de ejemplo, filtro Todo/PRs/Commits y hilos con `aria-expanded`; test de despliegue por teclado
- [x] 3.2 `ReviewCard` con estados en curso/completada/fallida, `border-beam` y `thinking-orbs`; test de cada estado
- [x] 3.3 Fallback con `prefers-reduced-motion`; test que lo verifique

## 4. Detalle, estadísticas y ajustes

- [x] 4.1 Detalle del change con dos reviews lado a lado (diff como bloque de código); test de render
- [x] 4.2 Pantallas `/stats` y `/settings` maquetadas con datos de ejemplo; test de render
- [x] 4.3 ADR en `docs/adr/` y actualización de la sección Frontend de `docs/spec/review-arena.md`; verificar enlaces
- [x] 4.4 Revisión visual con `pnpm dev` y capturas de las cuatro rutas
