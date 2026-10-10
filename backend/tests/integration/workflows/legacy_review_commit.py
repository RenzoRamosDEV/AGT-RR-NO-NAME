"""`ReviewCommitWorkflow` tal como era antes de los nombres legibles: el hijo se llama
`review-{change_id}-r{run}` y no lleva resumen ni detalles de usuario.

Igual que `legacy_review_change.py`, vive en un módulo mínimo porque el sandbox de workflows
reimporta el módulo que define la clase."""

from __future__ import annotations

from temporalio import workflow

from duelo.workflows.dto import ReviewChangeInput, ReviewCommitInput, RunReviewResult
from tests.integration.workflows.legacy_review_change import ReviewChangeWorkflowBeforeCompensation


@workflow.defn(name="ReviewCommitWorkflow")
class ReviewCommitWorkflowBeforeReadableNames:
    @workflow.run
    async def run(self, commit_input: ReviewCommitInput) -> list[RunReviewResult]:
        return await workflow.execute_child_workflow(
            ReviewChangeWorkflowBeforeCompensation.run,
            ReviewChangeInput(
                change_id=commit_input.change_id,
                agent_names=commit_input.agent_names,
                run=commit_input.run,
            ),
            id=f"review-{commit_input.change_id}-r{commit_input.run}",
        )
