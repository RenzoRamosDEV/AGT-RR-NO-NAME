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
