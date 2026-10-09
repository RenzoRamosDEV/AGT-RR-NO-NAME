from __future__ import annotations

from fastapi import APIRouter, Request

from duelo.entrypoints.api.schemas import AgentStatsResponse

router = APIRouter(tags=["stats"])


@router.get("/stats/agents", response_model=list[AgentStatsResponse])
async def agent_stats(request: Request) -> list[AgentStatsResponse]:
    stats = await request.app.state.dependencies.agent_stats()
    return [AgentStatsResponse.from_domain(s) for s in stats]
