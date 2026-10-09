# Tasks

## 1. Cliente y fuente de datos

- [x] 1.1 `DataSource.addProject`, `removeProject`, `syncPrs`; `request` lee `detail` y no parsea 204; `projects()` mapea `path`, `hooks_installed`, `github`; verificar con tests de `createHttpSource`
- [x] 1.2 Fuente de ejemplo con alta, baja y sincronización en memoria y las mismas reglas de error; verificar con tests de `createMockSource`

## 2. Sondeo

- [x] 2.1 `useAsync` con `pollMs`, `pollWhile`, `equals`, `refresh`, `updatedAt` y `refreshFailed`, y `PollingProvider`; verificar con tests de hook con temporizadores falsos (silencioso, pausa oculta, sin solape, `equals`, carga obsoleta, fallo)
- [x] 2.2 `useChannel` asocia «cargar más» a la clave de la consulta y conserva lo ya mostrado; verificar con test que no pierde ni duplica elementos al llegar uno nuevo
- [x] 2.3 Barra lateral, canal y detalle sondean (el detalle solo mientras no termine) con indicador «Actualizado hace N s»; verificar con test de integración

## 3. Alta de proyectos

- [x] 3.1 `Modal` accesible (foco inicial, Tab cíclico, Escape, devolver foco) y `lib/localPath`; verificar con tests de unidad y de integración
- [x] 3.2 `AddProjectDialog` y botón en barra lateral y estado vacío, errores por código y token en memoria; verificar con test de integración por cada código

## 4. Ajustes

- [x] 4.1 Lista de proyectos con ruta y hooks, «Sincronizar PRs» y «Quitar proyecto» con confirmación; verificar con test de integración

## 5. Cierre

- [x] 5.1 `pnpm lint`, `tsc -b`, `pnpm build` y `pnpm test` en verde
