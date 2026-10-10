# 0006. Logo de la aplicación según el tema

- Estado: Aceptada
- Fecha: 2026-10-10
- Complementa a: [0003](0003-frontend-estetica-github-slack.md)

## Contexto

La marca de Duelo era un SVG genérico de dos espadas cruzadas, sin relación con el producto. El
usuario aporta dos logos propios con fondo transparente (PNG de 500×500): un emblema neón de
burbujas de chat, con brillo morado y azul y el centro blanco con `<>`, pensado para el modo
oscuro; y el mismo icono en 3D acristalado, con el centro oscuro y `<>` cian, pensado para el modo
claro.

## Decisión

- **Neón para el oscuro y 3D para el claro.** Se probaron los dos logos sobre `#0d1117` y sobre
  `#ffffff` y la asignación de partida se confirma. El neón sobre blanco pierde su figura porque el
  centro blanco se funde con el fondo; el 3D sobre oscuro pierde el borde de la cabeza gris oscura.
- **Dos versiones de cada logo.** Un *emblema* (recorte de las dos cabezas centrales, sin burbujas
  sueltas) para la barra superior y los iconos, porque la composición completa es ilegible a 28 px;
  y un *héroe* (la composición completa, centrada en 480×320 sobre el color de la tarjeta de cada
  tema) para los estados vacíos y las páginas de no encontrado. El héroe lleva el fondo opaco a
  propósito: el efecto WebGL de `img-fx` pinta una textura y con transparencia no mostraría el color
  de la tarjeta.
- **Formatos.** Héroes en WebP (9 y 15 kB; los PNG pesaban unos 100 kB) y emblemas en PNG con alfa
  (3, 8 y 25-31 kB según tamaño). Los de 32 px quedan dentro del paquete principal (unos 7 kB).
- **Elección del logo.** `BrandLogo` y `HeroImage` leen el tema resuelto (`useResolvedTheme`), no
  solo `prefers-color-scheme`, así que siguen al selector Sistema/Claro/Oscuro. No hay parpadeo: el
  script de `index.html` fija `data-theme` antes de la primera pintura, el estado del tema usa la
  misma regla y `#root` está vacío hasta que React monta. El tamaño se reserva con `width` y
  `height`. Se descartó pintar las dos imágenes y ocultar una con CSS: carga siempre las dos y
  duplica el DOM sin evitar nada.
- **Favicon.** Dos `<link rel="icon">` con `media="(prefers-color-scheme: …)"`, uno por esquema del
  sistema (la pestaña sigue al sistema, no al selector de la aplicación) y el icono de Apple sobre
  `#0d1117`, porque iOS ignora el alfa. Se retira `favicon.svg`.
- **Las ilustraciones anteriores** (`hero-duelo.png` y `hero-review.png`) se sustituyen por el logo.
  La página de no encontrado también lo usa, en lugar del dibujo de líneas.

## Consecuencias

- El logo cambia con el tema en el mismo render que el resto de la interfaz.
- El peso de las imágenes de los estados vacíos baja de unos 146 kB a 24 kB entre los dos temas.
- El efecto de carga de `img-fx` sigue siendo un chunk aparte; reduced motion y los navegadores sin
  WebGL ven la misma imagen estática.
- Cambiar un logo exige regenerar sus tamaños (recorte, 32/64/128 px, héroe y favicon); el flujo
  está descrito en `openspec/changes/archive/*-app-logo-light-dark/design.md`.
