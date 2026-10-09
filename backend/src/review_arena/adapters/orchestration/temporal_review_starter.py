from __future__ import annotations

from temporalio.exceptions import WorkflowAlreadyStartedError

from review_arena.adapters.orchestration.temporal_client import LazyTemporalClient
from review_arena.application.ports import ReviewStartError
from review_arena.application.review_requests import ReviewCommitInput
from review_arena.domain.change import Change


class TemporalReviewStarter:
    """Arranca `ReviewCommitWorkflow` con un workflow id determinista: arrancar dos veces el
    mismo commit deja una sola ejecución (la segunda barrera de idempotencia)."""

    def __init__(self, client: LazyTemporalClient, agent_names: list[str]) -> None:
        self._client = client
        self._agent_names = agent_names

    async def start(self, change: Change) -> None:
        try:
            client = await self._client.get()
            await client.start_workflow(
                "ReviewCommitWorkflow",
                ReviewCommitInput(change_id=str(change.id), agent_names=self._agent_names),
                id=f"commit-{change.project_id}-{change.head_sha}",
                task_queue="platform",
            )
        except WorkflowAlreadyStartedError:
            return
        except Exception as exc:
            raise ReviewStartError("No se pudo arrancar la review") from exc
