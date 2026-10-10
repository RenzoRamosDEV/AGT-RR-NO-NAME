from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

from duelo.application.review_timeouts import RUN_REVIEW_START_TO_CLOSE
from duelo.workflows.dto import ReviewChangeInput, RunReviewInput, RunReviewResult
from duelo.workflows.review_details import render_details

RETRY = RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=1))

# Marca del historial: las ejecuciones que ya estaban en vuelo antes de existir la compensación
# se reproducen sin ella (no tienen el marcador), así que su replay no se rompe.
COMPENSATE_PATCH = "compensate-infra-failure"

# Marca del historial de los nombres legibles: las ejecuciones anteriores no la tienen, así que se
# reproducen con su id antiguo y sin resúmenes ni detalles de usuario.
READABLE_PATCH = "readable-workflow-names"


@workflow.defn
class ReviewChangeWorkflow:
    """Hijo: ejecuta un agente por cada nombre en `agent_names`, en paralelo (task queue
    `agents`). El fallo de un agente no bloquea al otro - cada activity `run_review`
    atrapa el error del agente y persiste una Review con estado `failed` en vez de
    propagar la excepción. Si la propia activity agota sus reintentos (fallo de
    infraestructura), el workflow registra la review fallida con una activity compensatoria
    en lugar de dejar el change sin rastro. Por Temporal viajan IDs y, de lo que responde
    cada reviewer, un extracto acotado (resumen, nota, hallazgos): cada activity carga el
    Change por su id y el diff nunca viaja."""

    @workflow.run
    async def run(self, review_input: ReviewChangeInput) -> list[RunReviewResult]:
        readable = workflow.patched(READABLE_PATCH)
        results: dict[str, RunReviewResult | None] = {}
        if readable:
            workflow.set_current_details(render_details(review_input.agent_names, results))

        async def review(name: str) -> RunReviewResult:
            result = await self._review_one(
                RunReviewInput(
                    change_id=review_input.change_id,
                    agent_name=name,
                    run=review_input.run,
                ),
                summary=_activity_summary(name, review_input.head_sha) if readable else None,
            )
            if readable:
                # El orden de llegada es el del historial: en el replay sale el mismo texto.
                results[name] = result
                workflow.set_current_details(render_details(review_input.agent_names, results))
            return result

        return list(await asyncio.gather(*(review(name) for name in review_input.agent_names)))

    async def _review_one(
        self, run_input: RunReviewInput, *, summary: str | None = None
    ) -> RunReviewResult:
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
                summary=summary,
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
                summary=f"{summary} (registra el fallo)" if summary else None,
            )
            return compensated


def _activity_summary(agent: str, head_sha: str) -> str:
    """Línea que Temporal muestra junto a la actividad: «claude revisa 3f2a9c1»."""
    return f"{agent} revisa {head_sha[:7]}".rstrip()


def _is_configuration_error(error: ActivityError) -> bool:
    cause = error.cause
    return isinstance(cause, ApplicationError) and cause.non_retryable
