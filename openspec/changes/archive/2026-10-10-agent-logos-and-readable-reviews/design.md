# Design

## Logos

`CLAUDE_LOGO.jpg` (400×400) y `CODEX_LOGO.jpg` (980×980, escala de grises) se reducen a 160×160
(dos veces el tamaño mayor de avatar, 36 px, para pantallas densas) y se importan como activos de
Vite desde `src/assets/agents/`. Los JPG traen su propio fondo (naranja y negro), así que se ven
bien sobre el tema claro y el oscuro sin tratamiento. Los originales de la raíz del repo no se
versionan.

`AgentAvatar` recibe `agent`, `size` (16, 20, 28 o 36) y `decorative` (por defecto `true`: la
imagen es `alt=""` y `aria-hidden`, porque el nombre ya está al lado). Con `decorative={false}`
el `alt` es el nombre del agente. Si la imagen falla (`onError`) o el agente es desconocido se
pintan las iniciales sobre un color estable por nombre (`agentHue`). Forma de cuadrado redondeado
(6 px; 4 px en 16 y 20 px) con un borde sutil, como un avatar de app de Slack.

## Mini-markdown seguro

`lib/markdown.ts` convierte texto a un árbol (`Block[]`/`Inline[]`) y `components/Markdown.tsx` lo
pinta con elementos de React. No hay `dangerouslySetInnerHTML`: todo texto pasa por React, que lo
escapa. Por eso `<script>` o `<img onerror>` salen como texto literal.

Soporta: párrafos (línea en blanco), saltos de línea simples (las reviews usan líneas con
significado), listas con viñetas y numeradas (con líneas de continuación), bloques con vallas
`` ``` ``, `` `código` ``, `**negrita**`, `*cursiva*` y enlaces `[texto](url)` o URLs sueltas.
Solo se enlaza `http:` y `https:` (`safeHttpUrl`), con `rel="noopener noreferrer"` y
`target="_blank"`. Las imágenes (`![alt](url)`) no existen: se muestran como texto.

El análisis es un recorrido lineal con `indexOf`, sin expresiones regulares con retroceso, y con
tope de profundidad (4) y de tamaño (100 000 caracteres; por encima se devuelve texto plano), para
que una entrada hostil no pueda bloquear el navegador.

## Hallazgos

`FindingCard` muestra icono y etiqueta de severidad (bug rojo, risk ámbar, improvement azul, nit
gris; las severidades desconocidas, neutras), la ubicación `archivo:línea` como chip con botón de
copiar (si no hay archivo no hay chip), el mensaje con markdown y, si el texto trae una etiqueta
`Arreglo:`, `Sugerencia:`, `Recomendación:`, `Fix:` o `Suggestion:`, la recomendación en un bloque
aparte (`lib/recommendation.ts`). Sin etiqueta, todo es mensaje.

`FindingsPanel` (detalle) agrupa por archivo como antes, añade un contador por severidad con
botones de filtro (`aria-pressed`) y reutiliza `FindingCard`. Las cards de review de runs
anteriores usan la misma lista.

## Plegado de textos largos

`Collapsible` pliega por longitud (más de 480 caracteres o 8 líneas en un resumen, más de 320 o 6
líneas en un hallazgo) y no por medición del DOM, para que sea determinista y se pueda probar en
jsdom. Plegado, limita la altura con un degradado y un botón «Ver más» (`aria-expanded`,
`aria-controls`). El estado abierto se guarda en un mapa de módulo con clave estable (id de la
review o del hallazgo): sobrevive al refresco por polling y a un remontaje del componente. El
mapa tiene tope (500 entradas) para no crecer sin límite.

## Ritmo de lectura

El texto va en una columna de unos 72 caracteres con `line-height` 1.6. Los datos de la review
(run, duración, nota) pasan a pills junto al nombre; hay una barra de color lateral sutil por
agente (`--avatar-hue`). Sin animaciones nuevas; los plegados no animan la altura.

## Alternativas descartadas

- Una librería de markdown (`react-markdown`, `marked`): decenas de kB y superficie de ataque para
  un subconjunto pequeño.
- Plegar midiendo `scrollHeight`: no funciona en jsdom y provoca parpadeo al refrescar.
