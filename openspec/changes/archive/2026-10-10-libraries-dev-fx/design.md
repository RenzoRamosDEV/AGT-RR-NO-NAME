# Design

## Un efecto por sitio, con criterio

| Librería | Dónde | Por qué ahí |
|---|---|---|
| `border-beam` | Filas del canal y panel de agentes del detalle, solo si `pending`/`running` | Marca visualmente lo que sigue en curso, que es justo lo que cambia con el sondeo de 5 s. |
| `thinking-orbs` | Ya existente (`Busy`, `PendingAgents`) | No se duplica; el beam y los orbes se complementan. |
| `liquid-gooey` | Indicador del selector de tema | Un indicador que se desliza entre tres opciones es el caso de uso de `move` («tab indicators»). |
| `metal-fx` | «Añadir proyecto» y «Reintentar review» | Son las acciones que más importan; un anillo en todos los botones sería ruido. |
| `img-fx` | Estados vacíos de la portada y del canal | Un héroe «cargando → imagen» da vida a una pantalla casi vacía y es decorativo. |

Se descartó usar `liquid-gooey` en el grupo de avatares de cada fila (una silueta con un solo color
perdería el color de cada agente) y `metal-fx` en la marca de la cabecera (aparece en todas las
páginas y es lo primero que se vería).

## Carga diferida y bundle

Medido con `pnpm build` partiendo del mismo punto (rama del rediseño):

| | Antes | Después |
|---|---|---|
| `index.js` (principal) | 344,18 kB (110,05 gzip) | 345,99 kB (110,70 gzip) |
| `BeamLayer` | — | 82,85 kB (12,73 gzip), al haber algo en curso |
| `FluidThemeSwitch` | — | 50,27 kB (17,11 gzip), tras el primer pintado |
| `MetalRing` | — | 87,92 kB (29,76 gzip), solo con WebGL2 |
| `HeroImageFx` (con `three`) | — | 593,91 kB (150,51 gzip), solo con WebGL y un estado vacío |

Importar las cuatro librerías de forma estática subía el principal a 570 kB (172 gzip), así que cada
una vive en su propio módulo detrás de `React.lazy`. Mientras llega el chunk se pinta la versión
estática (selector sin indicador, botón neutro, imagen fija, contenido sin envolver), de modo que
nunca hay saltos de maquetación ni pantallas en blanco.

## Degradación

Cada efecto cae a una versión estática si:
- el usuario pide `prefers-reduced-motion` (no se monta ningún canvas ni se carga el chunk);
- no hay WebGL (`hasWebGL`, con respuesta cacheada: jsdom y navegadores restringidos);
- el chunk aún no ha llegado.

`border-beam` y `liquid-gooey` no usan WebGL (CSS y SVG), así que solo dependen del movimiento
reducido y de la carga del chunk.

## Decisiones de integración (lo que salió al verlo con la API real)

- **`metal-fx` pone el fondo del botón transparente y pinta su propio núcleo** (blanco en el tema
  claro, gris oscuro en el oscuro). Un botón primario de texto blanco quedaba blanco sobre blanco.
  `MetalButton` usa siempre el aspecto neutro (`btn-metal`: color de texto normal y negrita), con o
  sin anillo, para que no haya salto al cargar el chunk.
- **`border-beam` en `line`.** Sobre un panel ancho, `size="md"` es un punto que recorre el
  perímetro y los modos `pulse-*` solo dejan un halo fuera del borde. El hilo inferior (`line`) se
  ve bien en filas y paneles, y da un único lenguaje visual a «en curso». El `.box` tiene
  `margin-bottom`, que quedaba dentro del envoltorio y alejaba el brillo del borde: el envoltorio
  hereda ese margen y el `.box` interior lo pierde.
- **`img-fx` y la revelación.** Se usa su planificador (`autoReveal` con un único pase: espera
  1,2–1,6 s, revela y mantiene la imagen un día) y no `triggerReveal` manual, que podía caer antes de
  que la imagen estuviera lista. El array de imágenes se memoiza: uno nuevo en cada render reiniciaba
  el efecto. Las ilustraciones son PNG, el formato de imagen para el que está pensada la librería.
  Con Chrome sin GPU (swiftshader) la revelación tarda unos 30 s; con GPU es casi inmediata.
- **Tema.** Los efectos leen el tema efectivo (`useResolvedTheme`) en lugar de `auto`, para seguir el
  selector de la aplicación y no solo el del sistema operativo.
- **Pruebas.** jsdom no tiene `ResizeObserver` ni `IntersectionObserver`: `test/setup.ts` los
  sustituye por observadores vacíos. Los tests de WebGL fingen `getContext` y sustituyen los módulos
  diferidos por marcadores, así que comprueban la lógica (qué se envuelve, cuándo, con qué tema) y no
  el dibujo.

## Fuera de alcance

- Efectos en el logo o en el diff, el agrupado líquido de avatares y el modo `dissolve`/`melt` de
  `liquid-gooey`: añadirían ruido sin aportar información.
- Una versión de pago (Pro) de las librerías: solo se usan los componentes gratuitos.
