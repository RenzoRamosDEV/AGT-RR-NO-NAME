"""Contrato de entrada del workflow de review, compartido por quien lo arranca (adaptador
de orquestación) y por el workflow mismo. Vive aquí porque `adapters/` y `workflows/` son
capas hermanas y no pueden importarse entre sí."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReviewCommitInput:
    change_id: str
    agent_names: list[str]
    run: int = 1
    # Datos de presentación: el workflow no puede leer la base de datos, así que el nombre legible
    # del hijo y los resúmenes de Temporal salen de aquí. Vacíos en las ejecuciones que ya estaban
    # en vuelo antes de existir (usan el nombre antiguo).
    kind: str = ""
    project_slug: str = ""
    project_id: str = ""
    head_sha: str = ""
    title: str = ""
