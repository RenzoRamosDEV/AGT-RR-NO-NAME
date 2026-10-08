from __future__ import annotations

from typing import Protocol

from review_arena.domain.change import Change
from review_arena.domain.events import ChangeCreated


class ChangeRepository(Protocol):
    async def add(self, change: Change, event: ChangeCreated) -> Change:
        """Persiste `change` y `event` en una única transacción.

        Si ya existía un `Change` con la misma identidad natural
        (project_id, kind, head_sha), lo devuelve sin crear un segundo evento.
        """
        ...
