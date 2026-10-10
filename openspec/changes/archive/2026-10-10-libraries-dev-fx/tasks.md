# Tasks

## 1. Dependencias y base

- [x] 1.1 Añadir `border-beam`, `liquid-gooey`, `metal-fx`, `img-fx` y `three`, y leer el README de cada una antes de usarla
- [x] 1.2 `components/fx/webgl.ts` (`hasWebGL(version)` cacheado), stubs de `ResizeObserver`/`IntersectionObserver` en `test/setup.ts`; verificar con los tests existentes en verde

## 2. border-beam

- [x] 2.1 `Beam`/`BeamLayer` (carga diferida, tema efectivo, sin movimiento reducido), en las filas `pending`/`running` del canal y en el panel de agentes del detalle; verificar con tests de unidad y de integración (solo lo en curso, pierde el beam al terminar)

## 3. liquid-gooey

- [x] 3.1 `ThemeSwitch` estático + `FluidThemeSwitch` diferido con indicador `move`, y `ThemeButton` compartido; verificar con tests (primer pintado usable, indicador que se desplaza, movimiento reducido)

## 4. metal-fx

- [x] 4.1 `MetalButton`/`MetalRing` en «Añadir proyecto» (portada y Ajustes) y «Reintentar review», siempre con el aspecto neutro `btn-metal`; verificar con tests (sin WebGL2, con WebGL2, movimiento reducido)

## 5. img-fx

- [x] 5.1 `HeroImage`/`HeroImageFx` diferido con `autoReveal` de un solo pase, dos ilustraciones PNG propias y `EmptyState hero`; verificar con tests (imagen fija sin WebGL/movimiento reducido, efecto con WebGL) y comprobar que `three` queda fuera del bundle principal

## 6. Cierre

- [x] 6.1 ADR 0004 con el criterio de cada efecto
- [x] 6.2 Capturas con Chrome headless contra la API real (canal en oscuro y claro, detalle, Ajustes, selector a mitad de transición, estados vacíos) y revisión visual
- [x] 6.3 `pnpm lint`, `tsc -b`, `pnpm build` y `pnpm test` en verde, y tamaños de bundle antes/después en `design.md`
