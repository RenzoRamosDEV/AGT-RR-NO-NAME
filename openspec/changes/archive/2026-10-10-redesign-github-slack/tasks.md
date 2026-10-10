# Tasks

## 1. Tema

- [x] 1.1 `styles/tokens.css` con la paleta oscura (por defecto) y clara (`data-theme`) y el respaldo sin JavaScript; verificar con `tokens.test.ts` (contraste AA de ambos temas, sin colores sueltos, script previo al primer pintado)
- [x] 1.2 `lib/theme.ts` (preferencia, resolución de «Sistema», `applyTheme`, almacén sincronizado) y el script de `index.html`; verificar con tests de unidad (guarda solo la preferencia, almacenamiento bloqueado, valor inválido)
- [x] 1.3 `ThemeSwitch` (cabecera y Ajustes) y `Busy` con el tema resuelto; verificar con tests de componente y de integración (ambos selectores en sincronía)

## 2. Marco

- [x] 2.1 Barra superior con marca y selector; barra lateral estilo Slack con Proyectos colapsable, «Añadir proyecto» y General; cajón y velo en móvil; verificar con tests de navegación y de orden de tabulación

## 3. Lista y mensajes

- [x] 3.1 `StatusIcon`, filas de PR, checks por agente, pestañas de estado con contadores de lo cargado, esqueletos y atajo «/»; verificar con tests de integración
- [x] 3.2 `ReviewCard` como mensaje de app, avatar con tono estable (`agentHue`) y color por severidad (`severityTone`, incluye `bug` y `risk`); verificar con tests de unidad e integración (tonos distintos para `agent_1`/`agent_2`)

## 4. Detalle, estadísticas y ajustes

- [x] 4.1 Detalle como conversación y «Archivos cambiados» (barra de cuadrados `diffSquares`, cabeceras de archivo y hunk, hallazgos sin duplicar, reviews por agente); verificar con tests de unidad e integración
- [x] 4.2 Tarjetas de resumen en estadísticas con medias ponderadas; Ajustes en cajas con Apariencia; verificar con tests de integración
- [x] 4.3 Estados vacíos, de error y 404 con ilustración (`EmptyState`); logo y favicon; verificar con test de integración

## 5. Cierre

- [x] 5.1 Retirar `border-beam`; ADR 0003 (sustituye al 0002) y `docs/spec/duelo.md`
- [x] 5.2 `biome check`, `tsc -b`, `pnpm build` y `pnpm test` en verde; revisión visual en claro, oscuro y móvil
