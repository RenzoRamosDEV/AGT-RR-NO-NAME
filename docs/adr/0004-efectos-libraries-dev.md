# 0004. Efectos de libraries.dev en la interfaz

- Estado: Aceptada
- Fecha: 2026-10-10
- Complementa a: [0003](0003-frontend-estetica-github-slack.md)

## Contexto

La estética de GitHub y Slack (ADR 0003) es sobria a propósito. Aun así, hay momentos en los que un
poco de movimiento dice algo que el texto no dice: qué sigue en curso, que algo cambió de estado,
que una pantalla vacía está «viva». libraries.dev ofrece componentes gratuitos para React (MIT, sin
dependencias salvo `three` en `img-fx`): `thinking-orbs`, `border-beam`, `liquid-gooey`, `metal-fx` e
`img-fx`. La pregunta no era si usarlos, sino dónde, para que cada uno aporte información y no
ruido.

## Decisión

Un efecto por sitio, cada uno con su motivo:

| Librería | Uso | Motivo |
|---|---|---|
| `thinking-orbs` | Cargas y agentes «revisando…» (`Busy`, `PendingAgents`) | Señala que algo está trabajando. Ya estaba. |
| `border-beam` | Hilo ámbar en el borde inferior de filas y panel de agentes en curso | Marca lo que sigue en curso, que es lo que cambia con el sondeo. |
| `liquid-gooey` | Indicador del selector de tema (`move`) | Un indicador que se desliza entre opciones es su caso de uso. |
| `metal-fx` | «Añadir proyecto» y «Reintentar review» | Resalta las dos acciones clave sin pintar todos los botones. |
| `img-fx` | Héroe de los estados vacíos de la portada y del canal | Da vida a una pantalla casi vacía, en un solo pase. |

Reglas comunes:

- **Decorativos y degradables.** Nunca llevan información que el texto no lleve ya; con
  `prefers-reduced-motion`, sin WebGL o mientras llega su chunk, la interfaz es la versión estática.
- **Cargados bajo demanda.** Cada librería vive en su módulo detrás de `React.lazy`; el bundle
  principal casi no crece (+1,8 kB) y `three` solo se descarga con WebGL y un estado vacío.
- **Leen el tema de la aplicación.** `useResolvedTheme`, no la preferencia del sistema, para seguir
  el selector.
- **Pocos puntos.** Se descartaron el agrupado líquido de avatares, un anillo metal en la marca de la
  cabecera y los modos `dissolve`/`melt`: más ruido que señal.

## Consecuencias

- `metal-fx` sustituye el fondo del botón por el suyo (blanco o gris oscuro), así que `MetalButton`
  usa siempre el aspecto neutro (`btn-metal`) con o sin anillo. Un botón primario de texto blanco
  quedaba blanco sobre blanco.
- `img-fx` está pensada para imágenes raster: las ilustraciones de marca son PNG y su revelación se
  delega en su planificador (un solo pase), con el array de imágenes memoizado.
- Hay cuatro dependencias nuevas (más `three`). Las dos que usan WebGL tienen alternativa estática;
  las otras dos (`border-beam`, `liquid-gooey`) son CSS y SVG.
- Los tests no dibujan: sustituyen los módulos diferidos y `getContext` y comprueban la lógica (qué
  se envuelve, cuándo, con qué tema, qué alternativa se muestra).
