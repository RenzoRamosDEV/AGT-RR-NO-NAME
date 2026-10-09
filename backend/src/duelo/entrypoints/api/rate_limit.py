from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status


def rate_limit(group: str) -> Callable[[Request], Awaitable[None]]:
    """Dependencia que limita por IP de cliente dentro de `group` (cada grupo cuenta aparte).

    Va antes de la autenticación: los intentos con token inválido también gastan cupo, que es lo
    que frena la fuerza bruta. Sin limitador configurado no hace nada."""

    async def dependency(request: Request) -> None:
        limiter = request.app.state.dependencies.rate_limiter
        if limiter is None:
            return
        # La IP es la del par TCP; tras un proxy hace falta `uvicorn --proxy-headers`.
        client = request.client.host if request.client else "unknown"
        decision = await limiter.hit(f"{group}:{client}")
        if not decision.allowed:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Demasiadas peticiones, reintenta más tarde",
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )

    return dependency
