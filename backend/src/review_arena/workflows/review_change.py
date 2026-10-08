from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from review_arena.workflows.dto import ReviewChangeInput, RunReviewInput, RunReviewResult

RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=1))


@workflow.defn
class ReviewChangeWorkflow:
    """Hijo: ejecuta un agente por cada nombre en `agent_names`, en paralelo (task queue
    `agents`). El fallo de un agente no bloquea al otro - cada activity `run_review`
    atrapa el error del agente y persiste una Review con estado `failed` en vez de
    propagar la excepción. Solo viajan IDs por Temporal: cada activity carga el Change
    por su id."""

    @workflow.run
    async def run(self, review_input: ReviewChangeInput) -> list[RunReviewResult]:
        # Las activities se registran como métodos de instancia de ReviewActivities
        # (para inyectar session_factory/agents sin estado global); los stubs de
        # tipos de temporalio no tipan bien esa referencia de método, así que se
        # llaman por su nombre de registro (igual al nombre del método) con
        # `result_type` explícito - el overload pensado para este caso.
        return list(
            await asyncio.gather(
                *(
                    workflow.execute_activity(
                        "run_review",
                        RunReviewInput(
                            change_id=review_input.change_id,
                            agent_name=name,
                            run=review_input.run,
                        ),
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
