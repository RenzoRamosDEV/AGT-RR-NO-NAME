# Proposal

## Why

La interfaz maquetada del change `redesign-frontend-black` es funcional pero básica: la barra
lateral no se adapta a pantallas pequeñas, el canal no se puede buscar, cada change obliga a
desplegar el hilo para saber cómo van sus reviews, el diff se muestra como texto plano y las
estadísticas son solo una tabla. Esta ronda 1 de mejoras (propuesta por Codex) pule esas cinco
áreas sin tocar el backend.

## What Changes

- **Sidebar móvil colapsable:** en pantallas estrechas la navegación se oculta tras un botón
  "Menú" (`aria-expanded`, `aria-controls`) y se cierra al navegar o con Escape.
- **Buscador del canal:** campo de búsqueda por título, autor o SHA que se combina con el filtro
  PR/Commit y distingue "canal vacío" de "sin coincidencias".
- **Resumen compacto por change:** cada card muestra cuántas reviews están completadas, en curso
  o fallidas sin desplegar el hilo.
- **Diff legible:** líneas numeradas (antigua/nueva), cabecera de archivo diferenciada, marca
  textual de añadido/borrado y aviso cuando el diff está truncado.
- **Estadísticas visuales:** barras compactas junto a `% útiles`, duración y fallos; la tabla y
  sus valores numéricos siguen siendo la fuente accesible.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities
- `frontend-shell`: añade navegación adaptable, búsqueda en el canal, resumen de reviews,
  visualización de diff y barras de estadísticas.

## Impact

- `frontend/src`: `layout/Shell.tsx`, `features/channel/ChannelPage.tsx`,
  `features/review/ChangeDetailPage.tsx`, `features/stats/StatsPage.tsx`, `data/mock.ts`,
  nuevos helpers en `lib/` y estilos en `index.css`.
- Sin dependencias nuevas, sin cambios de backend ni de API. Los datos siguen siendo mock.
