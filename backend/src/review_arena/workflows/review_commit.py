from __future__ import annotations

from temporalio import workflow

from review_arena.workflows.dto import RunReviewResult
from review_arena.workflows.review_change import ReviewChangeWorkflow


@workflow.defn
class ReviewCommitWorkflow:
    """Padre: arranca `ReviewChangeWorkflow` como hijo una vez para un `change_id`
    dado. El caller arranca este workflow con un workflow_id determinista (p. ej.
    `commit-{project_id}-{sha}`) para que arrancarlo dos veces para el mismo commit
    no duplique el trabajo - lo resuelve Temporal nativamente por `workflow_id`."""

    @workflow.run
    async def run(self, change_id: str, agent_names: list[str]) -> list[RunReviewResult]:
        return await workflow.execute_child_workflow(
            ReviewChangeWorkflow.run,
            args=[change_id, agent_names],
            id=f"review-{change_id}",
        )
