# Proposal

## Why

La interfaz actual es un tema negro puro con botones blancos y tarjetas planas: funciona, pero no
tiene jerarquía ni parece un producto serio. Duelo muestra commits y PRs (el mundo de GitHub) y las
respuestas de los agentes en un hilo (el mundo de Slack), así que el usuario ya sabe leer esos dos
lenguajes. Se pide un rediseño total con esa estética.

## What Changes

- **Temas.** Paleta de GitHub (Primer) en oscuro (por defecto) y claro, como tokens CSS, con
  selector Sistema / Claro / Oscuro en la cabecera y en Ajustes. Un script en `index.html` fija el
  tema antes del primer pintado; solo se guarda la preferencia. Se sustituye el «tema negro único».
- **Marco de la aplicación.** Barra superior (marca, selector de tema) y barra lateral estilo
  Slack: sección Proyectos colapsable como lista de canales (`#`), «+ Añadir proyecto» y General.
  En móvil la barra lateral es un cajón con velo.
- **Lista de changes como lista de PRs de GitHub.** Icono de estado con texto alternativo, título
  enlazado, `#sha · por autor · hace N min`, etiquetas Commit/PR, y a la derecha un «check» por
  agente; pestañas de estado con contadores de lo cargado; buscador con atajo `/`; densidad cómoda
  o compacta; esqueletos de carga.
- **Reviews como mensajes de Slack.** Avatar con color estable por agente, nombre, etiqueta `APP`,
  resumen, hallazgos con barra de color por severidad (incluye `bug` y `risk` del backend) y
  «reacciones» para run, duración y nota. Se retira `border-beam`.
- **Detalle como una PR.** Cabecera con la píldora de estado, conversación de los agentes
  (hallazgos una sola vez, agrupados), y «Archivos cambiados» con la barra de cinco cuadrados y el
  diff con cabeceras de archivo y de hunk al estilo GitHub.
- **Estadísticas** con tarjetas-resumen globales; **Ajustes** en cajas (Apariencia, General,
  Proyectos, Diagnóstico) con acciones destructivas en rojo.
- Estados vacíos, de error y 404 con ilustración y acción principal; logo y favicon nuevos.
- ADR 0003 sustituye al 0002.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities

- `frontend-shell`: se reemplaza el requisito del tema negro único y se redefinen la navegación,
  el estado de review en curso, el contraste y el indicador de carga; se añaden los requisitos de
  temas, marco, lista de PRs, mensajes, detalle, ajustes, estadísticas y estados vacíos.

## Impact

- Solo `frontend/` y documentación (`docs/adr`, `docs/spec/duelo.md`). Sin cambios de API ni de
  backend; sin dependencias nuevas (se elimina `border-beam`).
- Los tests que dependían de la estructura visual se actualizan; se añaden pruebas de tema,
  contraste en ambos temas, iconos de estado, mensajes, diff y atajo de teclado.
