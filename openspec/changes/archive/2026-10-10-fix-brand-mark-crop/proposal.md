# Proposal

## Why

El emblema de la barra superior se veía cortado: los recortes `mark-*` se hicieron demasiado
ajustados (para que se leyeran a 28 px) y dejaban las orejas de las dos cabezas y las burbujas
pegadas al borde del cuadrado. Además los recortes salían de los héroes, que son opacos, así que el
logo llevaba un fondo cuadrado propio.

## What Changes

- Los recortes `mark-dark-*` y `mark-light-*` (32, 64 y 128 px) se regeneran a partir de los
  originales transparentes: la composición completa, sin cortes, con ~6 % de margen y en un cuadrado
  exacto, con alfa.
- El emblema claro se obtiene quitando el fondo casi blanco del icono 3D original.
- Los favicons y el icono de Apple se regeneran desde los mismos recortes.
- El logo de la barra superior pasa de 28 a 40 px (la barra mide 48 px) para que la composición
  completa se distinga.

## Capabilities

### New Capabilities

(ninguna)

### Modified Capabilities

- `frontend-shell`: el logo se muestra completo.

## Impact

Solo `frontend/` (assets y `Shell.tsx`). Sin cambios de API ni de comportamiento.
