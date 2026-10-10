# Design

## Una sola fuente de verdad para el color

`styles/tokens.css` define todas las variables en tres bloques: oscuro (`:root`), claro
(`:root[data-theme="light"]`) y, solo para quien no ejecuta JavaScript, el claro bajo
`@media (prefers-color-scheme: light)` con `:root:not([data-theme])`. `index.css` solo usa
`var(--…)`; un test impide colores hexadecimales sueltos (salvo el blanco del texto del avatar).

El script de `index.html` pone `data-theme` antes del primer pintado: lee `duelo-theme` de
`localStorage` (si es `light` o `dark`) o, si no, `prefers-color-scheme`. En la app, `lib/theme.ts`
mantiene la preferencia en un almacén externo (`useSyncExternalStore`) para que el selector de la
cabecera y el de Ajustes estén siempre en sincronía, y `applyTheme()` resuelve «Sistema» y escucha
los cambios del sistema. `data-theme` está **siempre** presente tras el arranque (`dark` o
`light`), y de ahí lo leen tanto el CSS como `Busy`, que pasa el tema resuelto a `ThinkingOrb`
(antes lo fijaba a `dark`).

## Contraste AA medido, no supuesto

`tokens.test.ts` calcula el contraste WCAG de ambos temas: texto atenuado sobre las cuatro
superficies; `fg`, `accent`, `success`, `danger`, `warning` y `done` sobre las superficies y sobre
sus fondos tintados; el botón verde (normal y hover); la barra seleccionada de la barra lateral; y
el texto sobre los fondos del diff. Falló al principio y obligó a tres ajustes respecto a la paleta
de GitHub: hover del botón verde en oscuro (`#2ea043` → `#1a7f37`), ámbar del claro
(`#9a6700` → `#8a5d00`) y morado del claro (`#8250df` → `#7a45d6`).

## Contadores de la lista

La API pagina por cursor y no devuelve totales, así que la cabecera de la lista cuenta lo
**cargado** («5 cambios · 2 en curso · 2 con fallos · 1 completados») y añade «+» mientras haya
otra página. No se inventa un total.

## Mensajes de los agentes, sin duplicar hallazgos

`ReviewCard` es un mensaje (avatar, autor, `APP`, cuerpo, «reacciones»). Tiene `showFindings`: en
el hilo desplegable del canal los hallazgos van dentro del mensaje (no hay otro sitio); en el
detalle van **solo** en el panel agrupado por archivo, para no listarlos dos veces. Las reviews del
detalle se ordenan por agente (la API no garantiza orden).

Las severidades del backend (`bug`, `risk`, `improvement`, `nit`) entran en el orden y en
`severityTone`: `bug` y `critical`/`high` en rojo, `risk` y `medium` en ámbar, el resto neutro.

## Color de avatar

Un tono estable por agente, con un hash con mezcla final. La primera versión (`hash % 360`) daba a
`agent_1` y `agent_2` tonos a un grado de distancia, y otra salía negativa por el XOR con signo de
JavaScript; ambas las cazaron los tests (diferencia mínima entre nombres que solo difieren en un
carácter; rango 0–359).

## Sin sondeo ni orbes nuevos

El rediseño no toca el sondeo, los filtros del servidor ni las acciones. Los orbes siguen los
mismos estados que antes; `border-beam` desaparece porque el estado «revisando» ya es un mensaje
con orbe.

## Lo que no se hace

- Indicador de actividad por canal en la barra lateral: la API no da el número de changes en curso
  de cada proyecto y no se va a pedir una consulta por proyecto solo para un punto.
- Pestañas «Estadísticas del proyecto»: la API admite `?project=` pero el cliente aún no lo usa.
- «Zona de peligro» separada en Ajustes: quitar un proyecto es una acción por fila, en rojo y con
  confirmación, que es lo que ya existía.
- Toasts globales: las acciones se anuncian con avisos (`.notice`) junto a su control.
