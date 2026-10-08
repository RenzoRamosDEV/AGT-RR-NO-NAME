# Spec Delta

## Purpose

Permite al sistema recibir los datos de un cambio (commit o PR) de un proyecto y dejarlo
persistido junto con su evento de dominio de forma atómica y sin duplicados, para que
fases posteriores (workflows, API de ingesta) tengan una base fiable sobre la que disparar
reviews sin perder ni duplicar trabajo.

## ADDED Requirements

### Requirement: Persistencia atómica de un Change y su evento
El sistema SHALL persistir un `Change` nuevo y su evento `change.created` en una única
transacción: si cualquiera de las dos escrituras falla, ninguna de las dos debe quedar
persistida.

#### Scenario: Ingesta exitosa
- **WHEN** se ingesta un change válido para un proyecto existente
- **THEN** el `Change` queda persistido y existe exactamente un evento `change.created`
  asociado a él, visible en el mismo orden en que ocurrió

#### Scenario: Fallo durante la escritura del evento
- **WHEN** la escritura del `Change` se completa pero la escritura de su evento falla
- **THEN** la transacción se revierte por completo y el `Change` tampoco queda persistido

### Requirement: Identidad única por proyecto, tipo y referencia
El sistema SHALL tratar la combinación (proyecto, tipo de change, referencia de commit)
como la identidad natural de un `Change`: ingestar la misma combinación más de una vez
SHALL ser una operación idempotente, no SHALL crear una fila duplicada.

#### Scenario: Reingesta del mismo commit
- **WHEN** se ingesta dos veces un change con el mismo proyecto, tipo `commit` y el mismo
  `head_sha`
- **THEN** solo existe un `Change` para esa combinación y no se crea un segundo evento
  `change.created`

#### Scenario: Mismo commit, proyectos distintos
- **WHEN** dos proyectos distintos ingestan un change con el mismo `head_sha`
- **THEN** ambos quedan persistidos como `Change` independientes, cada uno con su propio
  evento
