from __future__ import annotations

import asyncio

from duelo.application.ports import ReviewStartError
from duelo.domain.change import Change


class FakeReviewStarter:
    """Registra qué commits arrancaron review y deduplica por (tipo, proyecto, sha, run), igual
    que el workflow id determinista del adaptador real. `yield_on_start` cede el control al
    arrancar para poder intercalar dos peticiones concurrentes."""

    def __init__(self, *, fail: bool = False, yield_on_start: bool = False) -> None:
        self.fail = fail
        self.yield_on_start = yield_on_start
        self.calls = 0
        self.started: dict[tuple[str, str, str, int], Change] = {}

    async def start(self, change: Change) -> None:
        self.calls += 1
        if self.yield_on_start:
            await asyncio.sleep(0)
        if self.fail:
            raise ReviewStartError("Temporal caído (simulado)")
        self.started.setdefault(
            (change.kind.value, str(change.project_id), change.head_sha, change.run), change
        )
