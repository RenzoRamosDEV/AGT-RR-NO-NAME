# Design

## Asignación de logos a temas

Se probaron los dos logos sobre los dos fondos (`#0d1117` y `#ffffff`). La asignación de partida se
confirma:

- **Neón → oscuro.** El brillo morado y azul y el centro blanco con `<>` destacan sobre fondo
  oscuro. Sobre blanco el centro blanco se funde con el fondo y el logo pierde su figura.
- **3D acristalado → claro.** El volumen y el `<>` cian se leen bien sobre blanco. Sobre oscuro la
  cabeza gris oscura pierde su borde, aunque el `<>` sigue visible.

## Dos versiones de cada logo

- **Emblema** (`mark-*`): recorte de las dos cabezas centrales, sin burbujas sueltas. Es la marca
  de la barra superior y de los favicons. La composición completa, de proporción 4:3 y con muchos
  detalles, queda como una mancha a 28 px.
- **Héroe** (`hero-*`): la composición completa recortada y centrada en un lienzo de 480×320 del
  color de la tarjeta (`--bg-subtle` de cada tema). Es la imagen de los estados vacíos. El lienzo
  tiene el fondo opaco a propósito: el efecto WebGL de `img-fx` pinta una textura, y con transparencia
  mostraría el color de fondo del contexto en vez del de la tarjeta.

Los héroes se guardan en WebP (9 y 15 kB) y los emblemas en PNG con alfa (3 a 31 kB).

## Cómo se elige el logo del tema

`BrandLogo` lee el tema resuelto con `useResolvedTheme()` y pinta una sola imagen. Es seguro frente
al parpadeo porque el script de `index.html` fija `data-theme` antes de la primera pintura y el
estado del tema (`lib/theme.ts`) se calcula con la misma regla; además el `#root` está vacío hasta
que React monta, así que no hay logo que corregir. Al cambiar el tema se actualiza la imagen en el
mismo render que el resto de la interfaz. La imagen lleva `width` y `height` explícitos para no mover
el diseño.

El héroe de los estados vacíos elige su imagen igual: `HeroImage` recibe una pareja `{ dark, light }`
y usa la del tema resuelto.

## Favicon

Dos `<link rel="icon">` con `media="(prefers-color-scheme: …)"`, uno por esquema del sistema (la
pestaña del navegador sigue al sistema, no al selector de la app). El icono de Apple se compone
sobre `#0d1117` porque iOS ignora el alfa.

## Alternativas descartadas

- **Renderizar las dos imágenes y ocultar una por CSS.** Evita cualquier parpadeo, pero carga las dos
  imágenes siempre y duplica el DOM. No hace falta porque no hay logo antes de que React monte.
- **Un solo logo para los dos temas.** Ninguno de los dos se ve bien en ambos fondos.
- **Manifest de la web app con icono de 512 px.** No se instala como aplicación; sin uso, no se genera.
