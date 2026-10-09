from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


async def periodic(
    interval_seconds: float,
    job: Callable[[], Awaitable[object]],
    *,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Ejecuta `job` ahora y luego cada `interval_seconds` hasta que se cancele. Un fallo del
    trabajo se registra y no detiene el bucle."""
    while True:
        try:
            await job()
        except Exception:
            logger.warning("Falló un trabajo periódico", exc_info=True)
        await sleep(interval_seconds)
