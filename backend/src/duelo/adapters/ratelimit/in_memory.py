"""Rate limiter de ventana deslizante en memoria de un solo proceso.

Con varios procesos (workers de uvicorn) cada uno lleva su propia cuenta, así que el límite
efectivo es N veces mayor; para eso haría falta otro adaptador (p. ej. Redis) tras el mismo
puerto. El estado se pierde al reiniciar."""

from __future__ import annotations

import math
import time
from collections import deque
from collections.abc import Callable

from duelo.application.ports import RateLimitDecision

_ALLOWED = RateLimitDecision(allowed=True, retry_after_seconds=0)


class InMemoryRateLimiter:
    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        if limit < 1 or window_seconds <= 0 or max_keys < 1:
            raise ValueError("limit, window_seconds y max_keys deben ser positivos")
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}

    async def hit(self, key: str) -> RateLimitDecision:
        now = self._clock()
        cutoff = now - self._window
        hits = self._hits.get(key)
        if hits is None:
            hits = self._hits[key] = deque()
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self._limit:
            # La más antigua sale de la ventana en `hits[0] + window`; se redondea hacia arriba.
            return RateLimitDecision(
                allowed=False, retry_after_seconds=max(1, math.ceil(hits[0] + self._window - now))
            )
        hits.append(now)
        if len(self._hits) > self._max_keys:
            self._shrink(cutoff)
        return _ALLOWED

    def _shrink(self, cutoff: float) -> None:
        """Acota la memoria: primero se descartan las claves sin actividad en la ventana y, si
        aun así sobran, las más antiguas por orden de inserción."""
        for key in [k for k, h in self._hits.items() if not h or h[-1] <= cutoff]:
            del self._hits[key]
        while len(self._hits) > self._max_keys:
            del self._hits[next(iter(self._hits))]
