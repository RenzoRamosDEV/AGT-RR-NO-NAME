# Tasks

## 1. Rutas con slug owner/repo

- [x] 1.1 `lib/projectPath.ts` (`projectPath`, `changePath`, `parseProjectPath`) con tests unitarios (un segmento, `owner/repo`, detalle, codificación, proyecto llamado `changes`, ruta vacía)
- [x] 1.2 Ruta única `p/*` con `ProjectRoute`; `ChannelPage` y `ChangeDetailPage` reciben `slug`/`id` por props; Shell, redirección de `/`, tarjetas y migas usan el helper

## 2. No encontrado

- [x] 2.1 `NotFoundPage` y ruta comodín; verificar con test de render (`/nada`, `/p`)

## 3. Regresión

- [x] 3.1 Mock `acme/widgets` y test de regresión de integración (raíz, canal y detalle con barra en el slug) con el origen en el comentario

## 4. Cierre

- [x] 4.1 `pnpm lint`, `tsc -b`, `pnpm build`, `pnpm test` en verde y comprobación con el stack real (`/`, canal y detalle)
