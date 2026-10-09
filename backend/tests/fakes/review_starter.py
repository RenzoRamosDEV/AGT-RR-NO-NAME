from __future__ import annotations

from review_arena.application.ports import ReviewStartError
from review_arena.domain.change import Change


class FakeReviewStarter:
    """Registra qué commits arrancaron review y deduplica por (proyecto, sha), igual que el
    workflow id determinista del adaptador real."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0
        self.started: dict[tuple[str, str], Change] = {}

    async def start(self, change: Change) -> None:
        self.calls += 1
        if self.fail:
            raise ReviewStartError("Temporal caído (simulado)")
        self.started.setdefault((str(change.project_id), change.head_sha), change)
