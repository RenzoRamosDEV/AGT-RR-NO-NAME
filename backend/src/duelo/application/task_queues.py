"""Nombres de las task queues de Temporal, en un solo sitio.

Los usan a la vez el adaptador que arranca los workflows (`adapters/`), los propios workflows
(`workflows/`) y el worker; un literal distinto en cualquiera de ellos deja tareas que nadie
recoge, sin error alguno.
"""

from __future__ import annotations

# Workflows padre e hijo: orquestación sin efectos, corre en cualquier sitio.
PLATFORM_TASK_QUEUE = "platform"

# Activities que ejecutan los CLI de los agentes: solo en la máquina donde están autenticados.
AGENTS_TASK_QUEUE = "agents"
