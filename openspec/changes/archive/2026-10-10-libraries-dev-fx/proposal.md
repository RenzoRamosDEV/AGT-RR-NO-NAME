# Proposal

## Why

La interfaz ya usa `thinking-orbs` de libraries.dev, pero el resto de la librería gratuita
(`border-beam`, `liquid-gooey`, `metal-fx` e `img-fx`) no se aprovecha: el rediseño retiró
`border-beam` y las otras tres nunca se usaron. Queremos que cada una aparezca donde aporta algo
real, con estética sobria de GitHub + Slack, sin añadir peso al bundle principal y sin sacrificar
accesibilidad ni rendimiento.

## What Changes

- **`border-beam`** (`Beam`): un hilo ámbar recorre el borde inferior de lo que está en curso: las
  filas del canal con estado agregado `pending` o `running` y el panel «Revisión de los agentes» del
  detalle mientras falte alguna review. Una fila terminada no se envuelve.
- **`liquid-gooey`** (`ThemeSwitch`): el segmento activo del selector Sistema/Claro/Oscuro es un
  indicador líquido (efecto `move`) que se desliza a la opción elegida arrastrando una gota.
- **`metal-fx`** (`MetalButton`): anillo de metal líquido en las pocas acciones clave: «Añadir
  proyecto» (estado vacío y Ajustes) y «Reintentar review».
- **`img-fx`** (`HeroImage`): en el estado vacío de la portada (sin proyectos) y del canal (sin
  cambios), la ilustración de la marca aparece con el cargador «generando…» que se convierte en la
  imagen. Hay dos ilustraciones propias (`hero-duelo.png`, `hero-review.png`).
- **`thinking-orbs`** ya está en `Busy`/`PendingAgents`; no se duplica y convive con el beam.
- Todas las librerías se cargan con `React.lazy` en su propio chunk: el bundle principal no crece
  (`three`, de `img-fx`, solo se descarga si hay WebGL y se muestra un estado vacío).
- Con `prefers-reduced-motion`, sin WebGL (jsdom, navegadores restringidos) o mientras llega el
  chunk, cada efecto se degrada a su versión estática: contenido sin envolver, selector con el botón
  pulsado teñido, botón neutro e imagen fija.
- ADR 0004 documenta qué efecto usa cada librería y por qué.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: efectos de libraries.dev (beam de lo que está en curso, selector de tema
  líquido, botones metal y héroe de los estados vacíos) con degradación y carga diferida.

## Impact

- `frontend/src`: nuevo `components/fx/` (`Beam`, `BeamLayer`, `MetalButton`, `MetalRing`,
  `HeroImage`, `HeroImageFx`, `webgl`), `components/FluidThemeSwitch.tsx` y `ThemeButton.tsx`,
  `ThemeSwitch` reescrito, cambios en `ChannelPage`, `ChangeDetailPage`, `RetryReview`,
  `ProjectsSettings`, `App`, `EmptyState`, estilos, `test/setup.ts` (stubs de observadores) y tests;
  dos ilustraciones en `src/assets`.
- Dependencias nuevas: `border-beam`, `liquid-gooey`, `metal-fx`, `img-fx` y `three` (peer de
  `img-fx`). Sin cambios de backend ni de contrato.
