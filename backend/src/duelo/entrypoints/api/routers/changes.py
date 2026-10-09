from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from duelo.application.ports import ReviewStartError
from duelo.application.retry_review import ChangeNotFound, RetryNotAllowed
from duelo.entrypoints.api.auth import require_ingest_token
from duelo.entrypoints.api.schemas import ChangeDetailResponse, ErrorResponse, RetryReviewResponse

router = APIRouter(tags=["changes"])


@router.get(
    "/changes/{change_id}",
    response_model=ChangeDetailResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_change(change_id: UUID, request: Request) -> ChangeDetailResponse:
    detail = await request.app.state.dependencies.get_change(change_id)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Change inexistente")
    return ChangeDetailResponse.from_detail(detail)


@router.post(
    "/changes/{change_id}/retry",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RetryReviewResponse,
    dependencies=[Depends(require_ingest_token)],
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def retry_review(change_id: UUID, request: Request) -> RetryReviewResponse:
    """Nueva ejecución de la review de un change cuya ejecución actual terminó con fallos."""
    try:
        change = await request.app.state.dependencies.retry_review(change_id)
    except ChangeNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Change inexistente") from exc
    except RetryNotAllowed as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except ReviewStartError as exc:
        # `run` no avanzó: reenviar la misma petición es seguro.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "No se pudo arrancar la review, reintenta"
        ) from exc
    return RetryReviewResponse(change_id=change.id, run=change.run)
