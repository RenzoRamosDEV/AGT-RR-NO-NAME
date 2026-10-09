from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from review_arena.application.ingest_commit import ProjectNotFound
from review_arena.application.ports import ReviewStartError
from review_arena.entrypoints.api.auth import require_ingest_token
from review_arena.entrypoints.api.schemas import (
    ErrorResponse,
    IngestCommitRequest,
    IngestCommitResponse,
)

router = APIRouter(tags=["ingest"], dependencies=[Depends(require_ingest_token)])


@router.post(
    "/ingest/commit",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestCommitResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def ingest_commit(body: IngestCommitRequest, request: Request) -> IngestCommitResponse:
    try:
        change = await request.app.state.dependencies.ingest_commit(body.to_submission())
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
    return IngestCommitResponse(change_id=change.id, diff_truncated=change.diff_truncated)
