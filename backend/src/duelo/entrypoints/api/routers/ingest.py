from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from duelo.application.ingest_commit import ProjectNotFound
from duelo.application.ports import ReviewStartError
from duelo.domain.change import Change
from duelo.entrypoints.api.auth import require_ingest_token
from duelo.entrypoints.api.schemas import (
    ErrorResponse,
    IngestCommitRequest,
    IngestCommitResponse,
    IngestPrRequest,
    IngestPrResponse,
)

router = APIRouter(tags=["ingest"], dependencies=[Depends(require_ingest_token)])

_ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


async def _run(ingest: Callable[[], Awaitable[Change]]) -> Change:
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
    change = await _run(lambda: request.app.state.dependencies.ingest_commit(body.to_submission()))
    return IngestCommitResponse(change_id=change.id, diff_truncated=change.diff_truncated)


@router.post(
    "/ingest/pr",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestPrResponse,
    responses=_ERRORS,
)
async def ingest_pr(body: IngestPrRequest, request: Request) -> IngestPrResponse:
    change = await _run(lambda: request.app.state.dependencies.ingest_pr(body.to_submission()))
    return IngestPrResponse(change_id=change.id, diff_truncated=change.diff_truncated)
