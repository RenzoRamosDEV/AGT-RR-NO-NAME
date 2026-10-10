# 0003. Frontend con la estética de GitHub y Slack

- Estado: Aceptada
- Fecha: 2026-10-10
- Sustituye a: [0002](0002-frontend-tema-negro.md)

## Contexto

El tema negro único del ADR 0002 se quedó corto en cuanto la interfaz tuvo datos reales: negro
puro con botones blancos, tarjetas planas sin jerarquía y una lista de changes que no se
distinguía de un volcado de texto. Duelo se usa al lado de GitHub (los changes son commits y PRs)
y de un chat de equipo (las reviews de los agentes son respuestas en un hilo), así que el
producto gana si se parece a lo que su usuario ya sabe leer.

## Decisión

Dos referencias, cada una para lo que mejor resuelve:

- **GitHub (Primer) para el contenido.** Paleta oscura por defecto y paleta clara, ambas como
  tokens CSS (`styles/tokens.css`); radios de 6 px, bordes de 1 px, sombras mínimas y anillo de
  foco azul. La lista de changes es una lista de PRs (icono de estado, título enlazado,
  `#sha · por autor · hace N min`, etiquetas, y a la derecha un «check» por agente). El diff es el
  de GitHub: cabecera por archivo con `+N −M` y la barra de cinco cuadrados, numeración y fondos
  verde/rojo. Ajustes se organiza en cajas con título, como los Settings de GitHub.
- **Slack para la conversación.** Barra lateral con el espacio de trabajo, la sección Proyectos
  como lista de canales (`#`, colapsable) y General; en el detalle, cada review es un **mensaje
  de una app**: avatar con color estable por agente, nombre, etiqueta `APP`, resumen, hallazgos con
  barra de color por severidad y «reacciones» para run, duración y nota. El agente que aún no ha
  contestado es el indicador de «escribiendo» (el orbe de `thinking-orbs`).

Tema: **Sistema / Claro / Oscuro**, elegido en la cabecera y en Ajustes. Un script en `index.html`
fija `data-theme` antes del primer pintado (sin parpadeo) a partir de la preferencia guardada o
del sistema; sin JavaScript manda `prefers-color-scheme`. Solo se guarda la preferencia
(`localStorage`, clave `duelo-theme`).

## Consecuencias

- El contraste AA de **ambos** temas se comprueba en `frontend/src/styles/tokens.test.ts` (texto,
  tonos sobre sus fondos, botón verde, barra seleccionada y diff). Esa prueba ya obligó a
  oscurecer tres colores de la paleta de referencia (verde del hover, ámbar y morado del tema
  claro), que no llegaban a 4,5:1.
- Sin colores sueltos: todo sale de las variables; un test impide añadir colores hexadecimales
  fuera de `tokens.css`.
- Se retira `border-beam` (el borde animado de la review en curso): en un mensaje al estilo Slack
  el estado «revisando» ya lo da el orbe. Queda `thinking-orbs`, que sigue el tema (`data-theme`)
  y no monta canvas bajo `prefers-reduced-motion`. Las microinteracciones (140 ms) también se
  desactivan con movimiento reducido.
- Los iconos son SVG propios en línea: no se añade ninguna dependencia.
- El contador de la cabecera de la lista cuenta lo cargado, no el total del servidor (la API
  pagina por cursor y no devuelve totales); lo indica con un «+» mientras haya más páginas.

Cambio de OpenSpec: `redesign-github-slack`.
