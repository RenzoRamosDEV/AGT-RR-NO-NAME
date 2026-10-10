from __future__ import annotations

from temporalio import workflow

from duelo.application.workflow_naming import (
    child_workflow_id,
    legacy_child_workflow_id,
    static_details,
    static_summary,
)
from duelo.workflows.dto import (
    ReviewChangeInput,
    ReviewCommitInput,
    RunReviewResult,
)
from duelo.workflows.review_change import READABLE_PATCH, ReviewChangeWorkflow


# Semántica Auto-Upgrade, como el hijo: los cambios de comandos van bajo `workflow.patched`
# (docs/adr/0007); sin `versioning_behavior`, que el servidor real rechaza sin Worker Versioning.
@workflow.defn
class ReviewCommitWorkflow:
    """Padre: arranca `ReviewChangeWorkflow` como hijo una vez para un `change_id` dado.

    El caller lo arranca con un workflow_id determinista y legible
    (`{kind}-{repo}-{sha12}-{proyecto}`, ver `application/workflow_naming.py`): arrancarlo dos veces
    para el mismo commit no duplica el trabajo, lo resuelve Temporal por `workflow_id`.

    El id del hijo, `review-{kind}-{repo}-{sha12}-{proyecto}-r{run}`, lleva el tipo (un commit y una
    PR con el mismo SHA son changes distintos) y el `run` (un rerun no choca con el anterior). Las
    ejecuciones anteriores a los nombres legibles, o sin los datos de presentación en la entrada,
    conservan el id antiguo del hijo."""

    @workflow.run
    async def run(self, commit_input: ReviewCommitInput) -> list[RunReviewResult]:
        readable = workflow.patched(READABLE_PATCH) and bool(
            commit_input.kind
            and commit_input.project_slug
            and commit_input.project_id
            and commit_input.head_sha
        )
        if not readable:
            return await workflow.execute_child_workflow(
                ReviewChangeWorkflow.run,
                ReviewChangeInput(
                    change_id=commit_input.change_id,
                    agent_names=commit_input.agent_names,
                    run=commit_input.run,
                ),
                id=legacy_child_workflow_id(commit_input.change_id, commit_input.run),
            )

        return await workflow.execute_child_workflow(
            ReviewChangeWorkflow.run,
            ReviewChangeInput(
                change_id=commit_input.change_id,
                agent_names=commit_input.agent_names,
                run=commit_input.run,
                head_sha=commit_input.head_sha,
            ),
            id=child_workflow_id(
                commit_input.kind,
                commit_input.project_slug,
                commit_input.head_sha,
                commit_input.project_id,
                commit_input.run,
            ),
            static_summary=static_summary("review", commit_input.project_slug, commit_input.title),
            static_details=static_details(
                kind=commit_input.kind,
                slug=commit_input.project_slug,
                sha=commit_input.head_sha,
                title=commit_input.title,
                change_id=commit_input.change_id,
                run=commit_input.run,
            ),
        )
