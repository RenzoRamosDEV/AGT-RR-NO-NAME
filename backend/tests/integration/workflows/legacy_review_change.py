"""`ReviewChangeWorkflow` tal como era antes de la compensación del fallo de infraestructura.

Vive en un módulo propio y mínimo (solo Temporal y los DTO) porque el sandbox de workflows
reimporta el módulo que define la clase: un módulo de test con SQLAlchemy o testcontainers no
pasaría la validación."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from duelo.workflows.dto import ReviewChangeInput, RunReviewInput, RunReviewResult

RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=1))


@workflow.defn(name="ReviewChangeWorkflow")
class ReviewChangeWorkflowBeforeCompensation:
    @workflow.run
    async def run(self, review_input: ReviewChangeInput) -> list[RunReviewResult]:
        return list(
            await asyncio.gather(
                *(
                    workflow.execute_activity(
                        "run_review",
                        RunReviewInput(review_input.change_id, name, review_input.run),
                        task_queue="agents",
                        result_type=RunReviewResult,
                        start_to_close_timeout=timedelta(minutes=5),
                        heartbeat_timeout=timedelta(seconds=30),
                        retry_policy=RETRY,
                    )
                    for name in review_input.agent_names
                )
            )
        )
