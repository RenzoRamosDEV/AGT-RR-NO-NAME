from __future__ import annotations

from temporalio import workflow

from duelo.workflows.dto import (
    ReviewChangeInput,
    ReviewCommitInput,
    RunReviewResult,
)
from duelo.workflows.review_change import ReviewChangeWorkflow


@workflow.defn
class ReviewCommitWorkflow:
    """Padre: arranca `ReviewChangeWorkflow` como hijo una vez para un `change_id`
    dado. El caller arranca este workflow con un workflow_id determinista (p. ej.
    `commit-{project_id}-{sha}`) para que arrancarlo dos veces para el mismo commit
    no duplique el trabajo - lo resuelve Temporal nativamente por `workflow_id`.
    El id del hijo incluye el número de `run` para que un rerun futuro no choque."""

    @workflow.run
    async def run(self, commit_input: ReviewCommitInput) -> list[RunReviewResult]:
        return await workflow.execute_child_workflow(
            ReviewChangeWorkflow.run,
            ReviewChangeInput(
                change_id=commit_input.change_id,
                agent_names=commit_input.agent_names,
                run=commit_input.run,
            ),
            id=f"review-{commit_input.change_id}-r{commit_input.run}",
        )
