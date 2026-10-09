from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status

from duelo.application.ingest_commit import ProjectNotFound
from duelo.entrypoints.api.schemas import AgentStatsResponse, ErrorResponse

router = APIRouter(tags=["stats"])

MAX_PROJECT = 255
# Sin NUL: Postgres no lo admite en texto. Al ir en el esquema, el contrato lo declara y el 422 es
# el estándar de FastAPI (no un caso especial del handler).
NO_NUL = r"^[^\x00]*$"


@router.get(
    "/stats/agents",
    response_model=list[AgentStatsResponse],
    responses={404: {"model": ErrorResponse}},
)
async def agent_stats(
    request: Request,
    project: Annotated[str | None, Query(max_length=MAX_PROJECT, pattern=NO_NUL)] = None,
) -> list[AgentStatsResponse]:
    """Métricas por agente: globales, o solo de un proyecto (`project=owner/repo`)."""
    try:
        stats = await request.app.state.dependencies.agent_stats(project)
    except ProjectNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Proyecto desconocido: {exc.slug}") from exc
    return [AgentStatsResponse.from_domain(s) for s in stats]
