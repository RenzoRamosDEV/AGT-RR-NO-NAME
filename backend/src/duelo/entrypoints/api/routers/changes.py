from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from duelo.entrypoints.api.schemas import ChangeDetailResponse, ErrorResponse

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
