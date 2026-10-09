# frontend-shell Specification

## Purpose
Define la apariencia y navegación base de la interfaz web de Review Arena: un tema negro único,
una estructura de canales por proyecto y una representación clara de los estados de review.

## Requirements

### Requirement: Tema negro único
La interfaz SHALL renderizarse siempre con un tema negro, independientemente de la preferencia
de color del sistema, sin parpadeo de otro tema en la carga.

#### Scenario: Sistema en modo claro
- **WHEN** el navegador declara `prefers-color-scheme: light` y se abre la aplicación
- **THEN** el fondo y las superficies son negros desde el primer pintado

### Requirement: Navegación por canales
La interfaz SHALL mostrar una barra lateral con un canal por proyecto y una sección General con
enlaces a Estadísticas y Ajustes, y SHALL marcar el destino activo.

#### Scenario: Abrir un canal
- **WHEN** el usuario selecciona un proyecto en la barra lateral
- **THEN** la ruta es `/p/:slug` y el canal aparece marcado como activo

### Requirement: Hilos de reviews desplegables
Cada change del canal SHALL permitir desplegar sus reviews por agente, exponiendo su estado
con `aria-expanded` y operable con teclado.

#### Scenario: Desplegar con teclado
- **WHEN** el usuario enfoca "Ver respuestas" y pulsa Enter
- **THEN** se muestran las reviews de cada agente y `aria-expanded` pasa a `true`

### Requirement: Estado de review en curso
Una review en curso SHALL mostrar una animación de carga de IA; una completada o fallida SHALL
mostrarse sin animación y con indicación textual del estado.

#### Scenario: Review en curso
- **WHEN** una review está en estado "en curso"
- **THEN** se muestra un indicador animado de "pensando" y un borde animado

#### Scenario: Movimiento reducido
- **WHEN** el usuario tiene `prefers-reduced-motion: reduce`
- **THEN** las animaciones de carga se sustituyen por un indicador estático con texto

### Requirement: Contraste accesible
El texto y los controles interactivos SHALL cumplir contraste WCAG AA sobre el fondo negro.

#### Scenario: Texto secundario
- **WHEN** se muestra texto atenuado sobre una superficie
- **THEN** su ratio de contraste es al menos 4.5:1
