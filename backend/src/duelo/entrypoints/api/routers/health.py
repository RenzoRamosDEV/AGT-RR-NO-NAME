from __future__ import annotations

import asyncio
import time
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from duelo.entrypoints.api.dependencies import Check
from duelo.entrypoints.api.schemas import DependenciesHealthResponse, DependencyHealthResponse

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


async def _probe(check: Check) -> DependencyHealthResponse:
    started = time.perf_counter()
    reason: Literal["timeout", "error"] | None = None
    try:
        await asyncio.wait_for(check(), READY_TIMEOUT_SECONDS)
    except TimeoutError:
        reason = "timeout"
    except Exception:  # noqa: BLE001 - el motivo es un vocabulario cerrado, nunca el error
        reason = "error"
    latency_ms = round((time.perf_counter() - started) * 1000)
    return DependencyHealthResponse(
        status="ok" if reason is None else "unavailable", latency_ms=latency_ms, reason=reason
    )


@ready_router.get("/health/dependencies", response_model=DependenciesHealthResponse)
async def dependencies_health(request: Request) -> DependenciesHealthResponse:
    """Diagnóstico: estado y latencia de cada dependencia. Siempre 200 (el sondeo para
    orquestadores es `/ready`); sin el texto de los errores, que puede llevar credenciales."""
    checks = request.app.state.dependencies.readiness_checks
    results = await asyncio.gather(*(_probe(check) for check in checks.values()))
    by_name = dict(zip(checks, results, strict=True))
    degraded = any(r.status != "ok" for r in results)
    return DependenciesHealthResponse(status="degraded" if degraded else "ok", dependencies=by_name)
