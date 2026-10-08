from __future__ import annotations

import time
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity
from temporalio.exceptions import ApplicationError

from review_arena.application.ports import ChangeRepository, ReviewAgent, ReviewRepository
from review_arena.application.record_review import record_review_failure, record_review_success
from review_arena.workflows.dto import ChangeDTO, RunReviewInput, RunReviewResult


class ReviewActivities:
    """Activities finas: delegan en los casos de uso de application/.

    No conoce qué adaptador concreto implementa cada puerto (`change_repository` y
    `review_repository` son fábricas inyectadas desde fuera, p. ej. la clase
    `SqlAlchemyChangeRepository` misma) - `workflows/` no puede importar `adapters/`
    directamente (capas hermanas en la regla de `import-linter`), así que la
    composición ocurre en quien construye esta instancia (el worker o el test).
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        change_repository: Callable[[AsyncSession], ChangeRepository],
        review_repository: Callable[[AsyncSession], ReviewRepository],
        agents: dict[str, ReviewAgent],
    ) -> None:
        self._session_factory = session_factory
        self._change_repository = change_repository
        self._review_repository = review_repository
        self._agents = agents

    @activity.defn
    async def load_change(self, change_id: str) -> ChangeDTO:
        async with self._session_factory() as session:
            change = await self._change_repository(session).get(UUID(change_id))

        if change is None:
            raise ApplicationError(f"Change {change_id} no existe", non_retryable=True)

        return ChangeDTO.from_domain(change)

    @activity.defn
    async def run_review(self, review_input: RunReviewInput) -> RunReviewResult:
        change = review_input.change.to_domain()
        agent = self._agents[review_input.agent_name]

        start = time.monotonic()
        try:
            result = await agent.review(change)
        except Exception as exc:  # noqa: BLE001 - el fallo del agente se registra, no se relanza
            duration_ms = int((time.monotonic() - start) * 1000)
            async with self._session_factory() as session:
                review = await record_review_failure(
                    self._review_repository(session),
                    change=change,
                    agent=review_input.agent_name,
                    run=review_input.run,
                    error=str(exc),
                    duration_ms=duration_ms,
                )
            return RunReviewResult(status="failed", review_id=str(review.id))

        duration_ms = int((time.monotonic() - start) * 1000)
        async with self._session_factory() as session:
            review = await record_review_success(
                self._review_repository(session),
                change=change,
                agent=review_input.agent_name,
                run=review_input.run,
                result=result,
                raw_output=None,
                duration_ms=duration_ms,
            )
        return RunReviewResult(status="completed", review_id=str(review.id))
