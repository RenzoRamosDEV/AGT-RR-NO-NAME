## ADDED Requirements

### Requirement: Commits deshechos y revertidos en el canal
La interfaz SHALL pintar la fila de un commit con `commit_state` `discarded` o `reverted` en ámbar
(fondo tintado y borde izquierdo ámbar con los tokens del tema, legible en oscuro y en claro), con un
icono de «deshacer» ámbar cuyo texto alternativo diga el estado, y SHALL mostrar en el centro de la
fila una etiqueta en mayúsculas («COMMIT DESHECHO» o «COMMIT REVERTIDO») con su subtítulo («Ya no
está en la rama» o «Revertido por `<sha corto>`»). El estado SHALL comunicarse también con texto y
no solo con el color. Las reviews, «Ver respuestas», los checks de los agentes y la vista compacta
SHALL seguir funcionando. Un commit deshecho o revertido SHALL contar como un cambio normal en los
contadores de revisión. La cabecera de la lista SHALL añadir los recuentos «N deshechos» y «N
revertidos» (de los cargados) cuando haya alguno.

#### Scenario: Commit deshecho
- **WHEN** un commit llega con `commit_state = discarded`
- **THEN** su fila es ámbar, muestra «COMMIT DESHECHO» y «Ya no está en la rama»

#### Scenario: Commit revertido
- **WHEN** un commit llega con `commit_state = reverted`
- **THEN** su fila muestra «COMMIT REVERTIDO» y «Revertido por <sha corto>»

#### Scenario: Vista compacta
- **WHEN** la densidad es compacta
- **THEN** la etiqueta se muestra en la misma línea y la fila sigue siendo ámbar

#### Scenario: Commit normal
- **WHEN** un commit es `active`
- **THEN** su fila no cambia

#### Scenario: Recuentos de la cabecera
- **WHEN** hay un commit deshecho y uno revertido entre los cargados
- **THEN** la cabecera de la lista dice «1 deshecho · 1 revertido» y los contadores de revisión no cambian

### Requirement: Aviso en el detalle de un commit deshecho o revertido
El detalle de un commit con `commit_state` `discarded` o `reverted` SHALL mostrar un aviso ámbar
destacado con el mismo texto que la fila y, si está revertido y se conoce el change del revert, un
enlace a él.

#### Scenario: Detalle de un commit revertido
- **WHEN** se abre el detalle de un commit revertido
- **THEN** aparece el aviso con «COMMIT REVERTIDO» y un enlace al change del revert
