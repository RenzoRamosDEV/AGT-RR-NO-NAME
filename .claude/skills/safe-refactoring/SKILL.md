---
name: safe-refactoring
description: Mantenibilidad - detecta duplicación, código muerto, funciones demasiado complejas, abstracciones innecesarias y violaciones de convenciones, y propone refactorizaciones que preservan el comportamiento. Úsalo cuando pidan "simplifica", "limpia", "¿hay duplicación o código muerto?" o al revisar un cambio que añade complejidad.
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git show:*), Bash(uv run ruff:*), Bash(uv run mypy:*), Bash(uv run pytest:*), Bash(uv run vulture:*)
---

# Mantenibilidad y refactor seguro

Propón refactors solo si reducen un coste real de mantener o de entender, y **solo si
preservan el comportamiento**. Esta skill no edita: describe el refactor y cómo
comprobar que es seguro.

## Qué buscar

- **Duplicación:** bloques casi idénticos en 3 o más sitios (dos veces aún no justifican
  abstraer). Sugiere extraer solo si las copias evolucionan juntas.
- **Código muerto:** funciones, parámetros, ramas o imports sin uso. Antes de llamarlo
  muerto, busca referencias dinámicas: workflows y activities (se registran y se llaman por
  nombre), entry points de uvicorn (`--factory`), migraciones de Alembic, fixtures de
  pytest, `__all__`. Una referencia por string cuenta.
- **Complejidad:** funciones largas, anidamiento profundo, muchas ramas, demasiados
  parámetros (apunta a agruparlos en un dataclass), banderas booleanas que cambian el
  comportamiento. `ruff` con reglas de complejidad ya marca lo extremo.
- **Abstracciones innecesarias:** capas que solo delegan, interfaces con una única
  implementación y sin segundo uso previsto, configuración para casos que no existen,
  manejo de errores para escenarios imposibles. Es regla del repo no diseñar por adelantado.
- **Nombres y comentarios:** nombres que mienten, comentarios que repiten el código o que
  ya no son ciertos. Un buen comentario explica el *porqué* (restricción oculta, bug que
  evita), no el *qué*.
- **Convenciones:** que el código nuevo se lea como el de al lado (idioma de comentarios,
  estilo de tests, nombres de fixtures, `from __future__ import annotations`). `ruff
  format` resuelve el formato; no lo comentes.
- **Tests:** duplicados o de relleno (ver `test-coverage`).

## Cómo proponer un refactor seguro

Cada propuesta incluye:

1. **Qué cambia** (antes/después en pocas líneas).
2. **Por qué es equivalente** en comportamiento (qué invariantes se mantienen).
3. **Red de seguridad:** qué tests lo cubren hoy (`just test-unit`, y `just mutation` si
   toca `domain`/`application`). Si no hay cobertura suficiente, el primer paso es
   añadirla, no refactorizar.
4. **Tamaño:** si el refactor es grande, divídelo en pasos que dejen el repo en verde.

## Lo que no es un hallazgo

Preferencias de estilo sin coste real, abstraer por "elegancia", o reescribir código que
funciona, está probado y no se va a tocar. Un refactor no pedido dentro de un commit de
otra cosa es, de hecho, un problema de atomicidad (`change-hygiene`).
