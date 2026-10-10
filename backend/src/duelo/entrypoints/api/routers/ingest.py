from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from duelo.application.ingest_commit import IngestResult, ProjectNotFound
from duelo.application.ports import ReviewStartError
from duelo.entrypoints.api.auth import require_ingest_token
from duelo.entrypoints.api.rate_limit import rate_limit
from duelo.entrypoints.api.schemas import (
    ErrorResponse,
    IngestCommitRequest,
    IngestCommitResponse,
    IngestPrRequest,
    IngestPrResponse,
)

# El límite va antes que el token: los intentos con token inválido también gastan cupo.
router = APIRouter(
    tags=["ingest"],
    dependencies=[Depends(rate_limit("ingest")), Depends(require_ingest_token)],
)

_ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


async def _run(ingest: Callable[[], Awaitable[IngestResult]]) -> IngestResult:
    try:
        return await ingest()
    except ProjectNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Proyecto desconocido: {exc.slug}") from exc
    except ValueError as exc:
        # Límites del dominio (NUL, longitudes): el mensaje no incluye datos internos.
        raise HTTPException(422, str(exc)) from exc
    except ReviewStartError as exc:
        # El Change ya quedó guardado: reenviar la misma petición es seguro.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "No se pudo arrancar la review, reintenta"
        ) from exc


@router.post(
    "/ingest/commit",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestCommitResponse,
    responses=_ERRORS,
)
async def ingest_commit(body: IngestCommitRequest, request: Request) -> IngestCommitResponse:
    result = await _run(lambda: request.app.state.dependencies.ingest_commit(body.to_submission()))
    return IngestCommitResponse(
        change_id=result.change.id,
        diff_truncated=result.change.diff_truncated,
        created=result.created,
    )


@router.post(
    "/ingest/pr",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestPrResponse,
    responses=_ERRORS,
)
async def ingest_pr(body: IngestPrRequest, request: Request) -> IngestPrResponse:
    result = await _run(lambda: request.app.state.dependencies.ingest_pr(body.to_submission()))
    return IngestPrResponse(
        change_id=result.change.id,
        diff_truncated=result.change.diff_truncated,
        created=result.created,
        reused=result.reused,
    )
