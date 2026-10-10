# Proposal

## Por qué

El flujo de Duelo atraviesa seis piezas (hook de git, API, Postgres, Temporal con dos colas,
workers y frontend) y ninguna doc lo cuenta de punta a punta ni deja verlo moverse. Quien
entra al proyecto tiene que reconstruirlo leyendo código. Se quiere una guía que explique
**cómo funciona y cómo se muestra** y que permita ver el viaje de un commit «en tiempo real»,
incluidos los casos de fallo y reintento, sin arrancar nada.

## Qué cambia

- **Nueva guía** `docs/flujo-duelo.html`: un solo archivo HTML autocontenido (CSS y JS inline,
  sin CDN, sin red, sin tracking) con el tema negro del ADR 0002.
- **Explicación detallada** de la arquitectura hexagonal, el flujo completo (hook → API →
  Postgres → Temporal → workers → Postgres → lectura → frontend), el reintento (`run + 1`) y
  una sección de **limitaciones reales**, todo con referencias `archivo:línea` comprobadas
  contra el código.
- **Simulador animado** con controles (reproducir, pausar, paso a paso, reiniciar, velocidad,
  teclado) y cinco escenarios: éxito, un agente falla y se reintenta, Temporal caído,
  commit duplicado y hook con la API caída. Paneles sincronizados: log, tablas, carriles de
  Temporal y maqueta del canal de la UI.
- Enlace desde `README.md`.

## Capacidades

Ninguna (documentación, `skip_specs: true`).

## Impacto

`docs/flujo-duelo.html`, `README.md`. Sin código del producto.
