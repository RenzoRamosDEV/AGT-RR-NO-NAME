# Tasks

## 1. Assets

- [x] 1.1 Emblemas `mark-dark-*`/`mark-light-*` (32, 64 y 128 px), héroes `hero-dark`/`hero-light` en WebP (480×320 sobre `--bg-subtle`), favicons por esquema y `apple-touch-icon.png`; retirar `favicon.svg`, `hero-duelo.png` y `hero-review.png`

## 2. Componentes

- [x] 2.1 `BrandLogo` con la versión del tema resuelto, `srcSet`, dimensiones explícitas y alternativa decorativa; sustituir `Logo` en la barra superior; tests unitarios
- [x] 2.2 `HeroImage` con pareja `{ dark, light }` y uso en los estados vacíos, el canal vacío y la página 404; tests de render
- [x] 2.3 `index.html` con los iconos por esquema y el icono de Apple; comprobar que no queda referencia al icono ni al SVG anteriores

## 3. Verificación

- [x] 3.1 Capturas de ambos logos sobre ambos fondos, barra superior y estado vacío en oscuro y claro, 404 y móvil; contraste AA del texto «Duelo»
- [x] 3.2 ADR 0006, `pnpm lint`, `tsc -b`, `pnpm build` y `pnpm test` en verde
