# Tasks

## 1. Hook: credenciales solo del fichero

- [x] 1.1 `load_config` sin override por entorno y con validación de URL `http(s)`; `main`/`_send_all` aceptan `--env-file`; verificar con tests unitarios (el entorno se ignora, URL con esquema inválido, fichero ausente) y un proceso real con `INGEST_URL` hostil en el entorno que no recibe nada

## 2. Instalador: ruta del fichero en el bloque

- [x] 2.1 `render_block` con `--env-file '<ruta>'` y reinstalación que actualiza un bloque antiguo; verificar con tests del instalador (ruta con comillas y espacios, idempotencia, bloque antiguo reemplazado)
- [x] 2.2 E2E real con `HOOK_ENV_PATH` fuera de `XDG_CONFIG_HOME` y de `HOME`: el commit llega a la API

## 3. Baja segura

- [x] 3.1 `remove_local_project` desinstala antes de borrar y lanza `HookRemovalFailed` si falla; verificar con fakes (orden, fallo conserva el proyecto, carpeta ausente completa, carrera 404)
- [x] 3.2 `DELETE /projects/{slug}` responde 409 con `detail` accionable y lo documenta en OpenAPI; verificar con test de API y contrato
- [x] 3.3 Ajustes muestra el `detail` del error al quitar un proyecto; verificar con test de interfaz

## 4. Cierre

- [x] 4.1 `just ci` en verde y mutación sobre los módulos tocados; docs y `docs/openapi.json` al día
