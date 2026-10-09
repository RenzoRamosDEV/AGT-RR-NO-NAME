from __future__ import annotations

from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from duelo.adapters.orchestration.temporal_client import LazyTemporalClient
from duelo.application.ports import ReviewStartError
from duelo.application.review_requests import ReviewCommitInput
from duelo.domain.change import Change


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
                # Una review completada no se relanza al reenviar el commit (gastaría a los
                # agentes otra vez); una que falló o se canceló sí puede reintentarse.
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
            )
        except WorkflowAlreadyStartedError:
            return
        except Exception as exc:
            raise ReviewStartError("No se pudo arrancar la review") from exc
