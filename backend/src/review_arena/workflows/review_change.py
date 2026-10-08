from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from review_arena.workflows.dto import ChangeDTO, RunReviewInput, RunReviewResult

RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=1))


@workflow.defn
class ReviewChangeWorkflow:
    """Hijo: carga el change una vez (task queue `platform`) y ejecuta un agente por
    cada nombre en `agent_names` en paralelo (task queue `agents`). El fallo de un
    agente no bloquea al otro - cada activity `run_review` atrapa el error del agente
    y persiste una Review con estado `failed` en vez de propagar la excepción."""

    @workflow.run
    async def run(self, change_id: str, agent_names: list[str]) -> list[RunReviewResult]:
        # Las activities se registran como métodos de instancia de ReviewActivities
        # (para inyectar session_factory/agents sin estado global); los stubs de
        # tipos de temporalio no tipan bien esa referencia de método, así que se
        # llaman por su nombre de registro (igual al nombre del método) con
        # `result_type` explícito - el overload pensado para este caso.
        change_dto = await workflow.execute_activity(
            "load_change",
            change_id,
            task_queue="platform",
            result_type=ChangeDTO,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RETRY,
        )

        return list(
            await asyncio.gather(
                *(
                    workflow.execute_activity(
                        "run_review",
                        RunReviewInput(change=change_dto, agent_name=name, run=1),
                        task_queue="agents",
                        result_type=RunReviewResult,
                        start_to_close_timeout=timedelta(minutes=5),
                        heartbeat_timeout=timedelta(seconds=30),
                        retry_policy=RETRY,
                    )
                    for name in agent_names
                )
            )
        )
