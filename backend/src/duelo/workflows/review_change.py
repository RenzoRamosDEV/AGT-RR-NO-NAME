from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

from duelo.application.review_timeouts import RUN_REVIEW_START_TO_CLOSE
from duelo.workflows.dto import ReviewChangeInput, RunReviewInput, RunReviewResult

RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=1))

# Marca del historial: las ejecuciones que ya estaban en vuelo antes de existir la compensación
# se reproducen sin ella (no tienen el marcador), así que su replay no se rompe.
COMPENSATE_PATCH = "compensate-infra-failure"


@workflow.defn
class ReviewChangeWorkflow:
    """Hijo: ejecuta un agente por cada nombre en `agent_names`, en paralelo (task queue
    `agents`). El fallo de un agente no bloquea al otro - cada activity `run_review`
    atrapa el error del agente y persiste una Review con estado `failed` en vez de
    propagar la excepción. Si la propia activity agota sus reintentos (fallo de
    infraestructura), el workflow registra la review fallida con una activity compensatoria
    en lugar de dejar el change sin rastro. Solo viajan IDs por Temporal: cada activity
    carga el Change por su id."""

    @workflow.run
    async def run(self, review_input: ReviewChangeInput) -> list[RunReviewResult]:
        return list(
            await asyncio.gather(
                *(
                    self._review_one(
                        RunReviewInput(
                            change_id=review_input.change_id,
                            agent_name=name,
                            run=review_input.run,
                        )
                    )
                    for name in review_input.agent_names
                )
            )
        )

    async def _review_one(self, run_input: RunReviewInput) -> RunReviewResult:
        # Las activities se registran como métodos de instancia de ReviewActivities
        # (para inyectar session_factory/agents sin estado global); los stubs de
        # tipos de temporalio no tipan bien esa referencia de método, así que se
        # llaman por su nombre de registro (igual al nombre del método) con
        # `result_type` explícito - el overload pensado para este caso.
        try:
            reviewed: RunReviewResult = await workflow.execute_activity(
                "run_review",
                run_input,
                task_queue="agents",
                result_type=RunReviewResult,
                start_to_close_timeout=RUN_REVIEW_START_TO_CLOSE,
                heartbeat_timeout=timedelta(seconds=30),
                retry_policy=RETRY,
            )
            return reviewed
        except ActivityError as error:
            # Un error de configuración (agente desconocido, change inexistente) no es un fallo
            # del agente: se propaga sin registrar nada para no contaminar las estadísticas.
            if _is_configuration_error(error) or not workflow.patched(COMPENSATE_PATCH):
                raise
            # Al no relanzar, `gather` no cancela a los demás agentes.
            compensated: RunReviewResult = await workflow.execute_activity(
                "record_review_infrastructure_failure",
                run_input,
                task_queue="agents",
                result_type=RunReviewResult,
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=RETRY,
            )
            return compensated


def _is_configuration_error(error: ActivityError) -> bool:
    cause = error.cause
    return isinstance(cause, ApplicationError) and cause.non_retryable
