# Design

## Un único archivo

HTML con `<style>` y `<script>` inline: se abre con doble clic (`file://`), se puede adjuntar
a un correo y no depende de ninguna red. Los tokens de color son los de
`frontend/src/styles/tokens.css`.

## Fidelidad: la guía cuenta lo que hace el código

- Cada afirmación técnica lleva su referencia `archivo:línea`, comprobada con `grep -n` y
  lectura del código en el momento de escribirla. Las rutas son relativas a
  `backend/src/duelo/` o `frontend/src/` según el prefijo.
- Lo que **no existe** se dice expresamente: solo hay `FakeAgent` (no hay adaptador de Claude ni
  de Codex), `heartbeat_timeout` sin latidos, `raw_output` siempre `None`, sin versionado de
  workflows, `docker-compose` sin worker, la UI mezcla reviews de varios runs.
- El hook se describe con el diseño tras `harden-local-project-hooks` (credenciales solo del
  fichero `hook.env`, cuya ruta viaja en el bloque instalado). Ese change se desarrolló en
  paralelo: el código del hook se cita por función, no por línea.

## Simulador

- **Estado derivado por reproducción:** el estado del escenario (tablas, carriles, log, UI) se
  reconstruye aplicando los pasos `0..n` sobre un estado inicial. Así «atrás», «reiniciar» y el
  enlace profundo (`#sim=fallo&paso=7`) dan siempre el mismo resultado.
- **Escenarios como listas de pasos** (título, explicación, referencia, nodos activos, paquete
  origen→destino, efecto sobre el estado). Los tramos comunes se comparten.
- **Animación:** los paquetes se mueven por el SVG con `requestAnimationFrame`; la duración se
  divide por la velocidad. Los efectos sobre el estado se aplican al llegar el paquete.
- **Accesibilidad:** región `aria-live` con el paso actual, controles reales (`button`), atajos
  de teclado dentro del simulador, contraste AA, responsive y `prefers-reduced-motion`
  (sin reproducción automática ni movimiento: se avanza paso a paso).

## Fuera de alcance

Datos en vivo de una instancia real (la guía es estática) y cualquier cambio en el producto.
