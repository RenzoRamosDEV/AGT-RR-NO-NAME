from __future__ import annotations

from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError, RPCStatusCode

from duelo.adapters.orchestration.temporal_client import LazyTemporalClient
from duelo.application.ports import ProjectSlugs, ReviewStartError
from duelo.application.review_requests import ReviewCommitInput
from duelo.application.task_queues import PLATFORM_TASK_QUEUE
from duelo.application.workflow_naming import (
    FALLBACK_REPO,
    legacy_parent_workflow_id,
    parent_workflow_id,
    safe_title,
    static_details,
    static_summary,
)
from duelo.domain.change import Change

# Estados con los que el id antiguo sigue «ocupando» al change: la ejecución está en marcha o
# terminó bien. Una que falló, se canceló, se terminó a mano o agotó su plazo sí se puede relanzar
# (es la misma regla que `ALLOW_DUPLICATE_FAILED_ONLY` aplica a un id igual).
_LIVE_STATUSES = frozenset(
    {
        WorkflowExecutionStatus.RUNNING,
        WorkflowExecutionStatus.COMPLETED,
        WorkflowExecutionStatus.CONTINUED_AS_NEW,
    }
)


class TemporalReviewStarter:
    """Arranca `ReviewCommitWorkflow` con un workflow id determinista y legible
    (`{kind}-{repo}-{sha12}-{proyecto6}`, más `-r{run}` desde el segundo run): arrancar dos veces el
    mismo change y run deja una sola ejecución (la segunda barrera de idempotencia) y un PR no se
    pisa con un commit del mismo sha. Antes de arrancar con el id nuevo consulta también el id
    antiguo (`{kind}-{proyecto}-{sha}`): si esa ejecución existe y no falló, no arranca otra, así
    que reenviar un commit que ya se revisó antes de los nombres legibles no vuelve a gastar a los
    agentes."""

    def __init__(
        self,
        client: LazyTemporalClient,
        agent_names: list[str],
        slugs: ProjectSlugs | None = None,
    ) -> None:
        self._client = client
        self._agent_names = agent_names
        self._slugs = slugs

    async def start(self, change: Change) -> None:
        try:
            slug = await self._slug_of(change)
            client = await self._client.get()
            if await _legacy_execution_is_taken(client, change):
                return
            kind = change.kind.value
            await client.start_workflow(
                "ReviewCommitWorkflow",
                ReviewCommitInput(
                    change_id=str(change.id),
                    agent_names=self._agent_names,
                    run=change.run,
                    kind=kind,
                    project_slug=slug,
                    project_id=str(change.project_id),
                    head_sha=change.head_sha,
                    # El título viaja en la entrada del workflow, que queda en el historial.
                    title=safe_title(change.title),
                ),
                id=workflow_id(change, slug),
                task_queue=PLATFORM_TASK_QUEUE,
                # Una review completada no se relanza al reenviar el commit (gastaría a los
                # agentes otra vez); una que falló o se canceló sí puede reintentarse.
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY,
                static_summary=static_summary(kind, slug, change.title),
                static_details=static_details(
                    kind=kind,
                    slug=slug,
                    sha=change.head_sha,
                    title=change.title,
                    change_id=str(change.id),
                    run=change.run,
                ),
            )
        except WorkflowAlreadyStartedError:
            return
        except Exception as exc:
            raise ReviewStartError("No se pudo arrancar la review") from exc

    async def _slug_of(self, change: Change) -> str:
        found = await self._slugs.slug_of(change.project_id) if self._slugs is not None else None
        return found or FALLBACK_REPO


async def _legacy_execution_is_taken(client: Client, change: Change) -> bool:
    handle = client.get_workflow_handle(
        legacy_parent_workflow_id(change.kind.value, change.project_id, change.head_sha, change.run)
    )
    try:
        description = await handle.describe()
    except RPCError as exc:
        if exc.status == RPCStatusCode.NOT_FOUND:
            return False
        raise
    return description.status in _LIVE_STATUSES


def workflow_id(change: Change, slug: str) -> str:
    return parent_workflow_id(
        change.kind.value, slug, change.head_sha, change.project_id, change.run
    )
