# Design

## Decisión

Se muestra la composición completa del logo (cabezas más burbujas) y no solo las cabezas. Recortar
las cabezas dejaba burbujas cortadas por el borde del cuadrado, que es justo el defecto que se vio.
Para que la composición completa sea legible a tamaño de barra se sube el logo a 40 px.

## Fuentes y proceso

- Oscuro: el PNG transparente de 500×500 del emblema neón, recortado con `-trim` al contenido.
- Claro: el icono 3D original (opaco, fondo casi blanco): se escala a 500 px y se vacía el fondo por
  relleno desde las cuatro esquinas con tolerancia del 7 %; después `-trim`.
- Cada recorte se encaja en un cuadrado transparente al 88 % del lado (margen ~6 % por lado) con
  `-gravity center -extent`, en 32, 64 y 128 px. Mismos nombres de fichero, así que `BrandLogo` y
  `brand.ts` no cambian.

## Riesgos

- En el tema claro las burbujas de cristal quedan muy difuminadas al quitar el fondo: es lo
  esperado sobre un fondo claro y no se ve ningún borde duro.
- No se mide el contraste del logo: es una imagen decorativa junto al texto «Duelo».
