from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from duelo.entrypoints.api.auth import require_operator_token
from duelo.entrypoints.api.schemas import ErrorResponse, RawOutputResponse

router = APIRouter(tags=["reviews"])


@router.get(
    "/reviews/{review_id}/raw-output",
    response_model=RawOutputResponse,
    dependencies=[Depends(require_operator_token)],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_raw_output(
    review_id: UUID, request: Request, response: Response
) -> RawOutputResponse:
    """Salida íntegra del agente, solo para el operador (`X-Operator-Token`). Es contenido sin
    filtrar sobre un diff privado: no se cachea y el detalle público nunca la incluye."""
    output = await request.app.state.dependencies.get_review_raw_output(review_id)
    if output is None:
        # Review inexistente o sin salida cruda (fallida): mismo 404, sin oráculo de ids.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sin salida cruda")
    response.headers["Cache-Control"] = "no-store"
    return RawOutputResponse.from_domain(output)
