# 0005. Logos de agentes y reviews legibles

- Estado: Aceptada
- Fecha: 2026-10-10
- Complementa a: [0003](0003-frontend-estetica-github-slack.md)

## Contexto

Con agentes reales (Claude Code y Codex) el hilo de reviews se veía mal: el resumen era un párrafo
pegado, los acentos graves (`` `código` ``) salían literales, los hallazgos eran citas oscuras con
mucho texto y la ruta del archivo quedaba diminuta al final. Además cada agente era un cuadrado de
color con una inicial.

## Decisión

- **Logos como avatar.** `claude` y `codex` (sin distinguir mayúsculas) usan su logo, reducido a
  160×160 (3,9 y 5,5 kB) en `src/assets/agents/`. Cualquier otro agente conserva las iniciales
  sobre un color estable por nombre. Un único `AgentAvatar` con tamaños 16, 20, 28 y 36, decorativo
  por defecto (el nombre ya está al lado) y con las iniciales como alternativa si la imagen falla.
- **Markdown mínimo y propio, no una librería.** Lo que escriben los agentes lleva un subconjunto
  de Markdown: párrafos, código en línea, negrita, cursiva, listas, bloques y enlaces http(s).
  Se pinta con elementos de React, nunca como HTML, así que no puede inyectar nada; no hay
  imágenes ni enlaces que no sean http o https. El análisis es lineal y con topes (20 000
  caracteres, 4 niveles de anidación). Una librería de Markdown costaría decenas de kB y
  ampliaría la superficie de ataque para un subconjunto pequeño.
- **Jerarquía de lectura.** Cabecera (agente, APP, estado, datos), bloque «Resumen» y «Hallazgos
  (N)» en columna de unos 72 caracteres con `line-height` 1.6. Cada hallazgo es una tarjeta con
  la severidad con icono y color, la ubicación `archivo:línea` como chip copiable y la
  recomendación (`Arreglo:`, `Sugerencia:`…) en un bloque aparte.
- **Plegado por longitud.** Un texto largo se pliega con «Ver más» y el estado abierto se recuerda
  fuera de React, con tope de 500 entradas, para que el refresco automático no lo vuelva a
  plegar. Se decide por longitud y no midiendo el DOM: es igual en cualquier pantalla y se
  puede probar.
- **Filtro por severidad** en el panel de hallazgos del detalle, con contadores.

## Consecuencias

- El texto de un hallazgo se ve distinto al que devuelve la API (formato, recomendación aparte),
  pero nunca se altera el dato: se interpreta solo al pintarlo.
- Un texto con Markdown fuera del subconjunto (tablas, citas, HTML) se muestra tal cual, sin
  formato. Es la parte que más puede pedir ampliarse.
- Los logos son marcas de terceros; se usan solo para identificar al agente.
