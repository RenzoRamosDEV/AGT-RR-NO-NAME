from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])
ready_router = APIRouter(tags=["health"])

READY_TIMEOUT_SECONDS = 3.0


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check: the API process is up. Does not check Postgres or Temporal."""
    return {"status": "ok"}


@ready_router.get("/ready", response_model=None)
async def ready(request: Request) -> JSONResponse:
    """Readiness: 200 solo si Postgres y Temporal responden; 503 indicando cuál falla."""
    checks = request.app.state.dependencies.readiness_checks

    async def _run(check) -> bool:  # type: ignore[no-untyped-def]
        try:
            await asyncio.wait_for(check(), READY_TIMEOUT_SECONDS)
        except Exception:  # noqa: BLE001 - cualquier fallo significa "no disponible"
            return False
        return True

    outcomes = await asyncio.gather(*(_run(check) for check in checks.values()))
    failing = [name for name, ok in zip(checks, outcomes, strict=True) if not ok]
    if failing:
        return JSONResponse({"status": "unavailable", "failing": failing}, status_code=503)
    return JSONResponse({"status": "ready"})
