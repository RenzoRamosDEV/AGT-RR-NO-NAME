"""Latidos de `run_review` y compensación del fallo de infraestructura, sin Temporal.

Los latidos se inyectan (un contador) y el intervalo se acorta: nada duerme de verdad."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from temporalio.exceptions import ApplicationError

from duelo.application.ingest_change import ingest_change
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ReviewFailed
from duelo.domain.review import ReviewResult
from duelo.workflows.activities import INFRASTRUCTURE_FAILURE_MESSAGE, ReviewActivities
from duelo.workflows.dto import RunReviewInput
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.review_repository import FakeReviewRepository
from tests.fakes.session import FakeSessionFactory

AGENT = "agent_slow"


class GatedAgent:
    """Agente que no termina hasta que el test lo libera (o lanza si se le pide)."""

    name = AGENT

    def __init__(self, *, fail_after_release: bool = False) -> None:
        self.release = asyncio.Event()
        self._fail = fail_after_release

    async def review(self, change: Change) -> ReviewResult:
        await self.release.wait()
        if self._fail:
            raise RuntimeError("el agente lento falló")
        return ReviewResult(summary="ok", score=5, findings=())


class Beats:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def __call__(self, *details: object) -> None:
        self.calls.append(details)


async def _world(agent: GatedAgent, beats: Beats, *, interval: float = 0.005):
    changes, reviews = FakeChangeRepository(), FakeReviewRepository()
    change = await ingest_change(
        changes,
        project_id=uuid4(),
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha="a" * 40,
        title="t",
        author="a",
        url="https://example.com",
        diff="d",
        diff_truncated=False,
    )
    activities = ReviewActivities(
        session_factory=FakeSessionFactory(),  # type: ignore[arg-type]
        change_repository=lambda _session: changes,
        review_repository=lambda _session: reviews,
        agents={AGENT: agent},  # type: ignore[arg-type]
        heartbeat=beats,
        heartbeat_interval=interval,
    )
    return activities, RunReviewInput(change_id=str(change.id), agent_name=AGENT, run=1), reviews


async def _wait_for_beats(beats: Beats, count: int) -> None:
    async with asyncio.timeout(5):
        while len(beats.calls) < count:
            await asyncio.sleep(0.001)


async def test_a_slow_agent_keeps_heartbeating_until_it_finishes() -> None:
    agent, beats = GatedAgent(), Beats()
    activities, review_input, _ = await _world(agent, beats)

    running = asyncio.create_task(activities.run_review(review_input))
    await _wait_for_beats(beats, 3)  # aún no ha terminado y ya late varias veces
    assert not running.done()
    agent.release.set()
    result = await running

    assert result.status == "completed"
    assert len(beats.calls) >= 3
    # Cada latido identifica qué revisión sigue viva.
    assert beats.calls[0] == (review_input.change_id, AGENT)


async def test_heartbeats_stop_once_the_agent_returns() -> None:
    agent, beats = GatedAgent(), Beats()
    activities, review_input, _ = await _world(agent, beats)
    agent.release.set()

    await activities.run_review(review_input)
    seen = len(beats.calls)
    await asyncio.sleep(0.05)  # diez intervalos: si la tarea siguiera viva, habría más latidos

    assert len(beats.calls) == seen


async def test_heartbeats_stop_when_the_agent_raises() -> None:
    agent, beats = GatedAgent(fail_after_release=True), Beats()
    activities, review_input, reviews = await _world(agent, beats)
    agent.release.set()

    result = await activities.run_review(review_input)
    seen = len(beats.calls)
    await asyncio.sleep(0.05)

    assert result.status == "failed"
    assert len(beats.calls) == seen
    assert len(reviews.persisted_events) == 1


async def test_without_an_activity_context_heartbeating_is_a_no_op() -> None:
    """Llamar a la activity como función (fuera de Temporal) no debe fallar por los latidos."""
    changes, reviews = FakeChangeRepository(), FakeReviewRepository()
    change = await ingest_change(
        changes,
        project_id=uuid4(),
        kind=ChangeKind.COMMIT,
        ref="r",
        head_sha="b" * 40,
        title="t",
        author="a",
        url="u",
        diff="d",
        diff_truncated=False,
    )
    agent = GatedAgent()
    agent.release.set()
    activities = ReviewActivities(
        session_factory=FakeSessionFactory(),  # type: ignore[arg-type]
        change_repository=lambda _session: changes,
        review_repository=lambda _session: reviews,
        agents={AGENT: agent},  # type: ignore[arg-type]
    )

    result = await activities.run_review(
        RunReviewInput(change_id=str(change.id), agent_name=AGENT, run=1)
    )

    assert result.status == "completed"


# --- compensación del fallo de infraestructura ---------------------------------------------


async def test_the_compensation_records_a_failed_review_with_a_generic_message() -> None:
    agent, beats = GatedAgent(), Beats()
    activities, review_input, reviews = await _world(agent, beats)

    result = await activities.record_review_infrastructure_failure(review_input)

    assert result.status == "failed"
    (event,) = reviews.persisted_events
    assert isinstance(event, ReviewFailed)
    assert event.error == INFRASTRUCTURE_FAILURE_MESSAGE
    stored = next(iter(reviews._by_natural_key.values()))
    assert (stored.agent, stored.run, stored.status.value) == (AGENT, 1, "failed")
    assert stored.error == INFRASTRUCTURE_FAILURE_MESSAGE
    # No filtra nada que pueda venir de la excepción original (rutas, SQL, credenciales).
    assert "postgres" not in (stored.error or "").lower()


async def test_the_compensation_is_idempotent() -> None:
    agent, beats = GatedAgent(), Beats()
    activities, review_input, reviews = await _world(agent, beats)

    first = await activities.record_review_infrastructure_failure(review_input)
    second = await activities.record_review_infrastructure_failure(review_input)

    assert first.review_id == second.review_id
    assert len(reviews.persisted_events) == 1  # un solo evento y una sola fila
    assert len(reviews._by_natural_key) == 1


async def test_the_compensation_does_not_overwrite_a_review_that_was_already_saved() -> None:
    """Si `run_review` llegó a guardar su resultado justo antes del fallo, la compensación no
    lo pisa ni crea un segundo evento."""
    agent, beats = GatedAgent(), Beats()
    activities, review_input, reviews = await _world(agent, beats)
    agent.release.set()
    done = await activities.run_review(review_input)

    compensated = await activities.record_review_infrastructure_failure(review_input)

    assert compensated.review_id == done.review_id
    assert compensated.status == "completed"
    assert len(reviews.persisted_events) == 1


async def test_the_compensation_of_a_missing_change_is_a_non_retryable_error() -> None:
    agent, beats = GatedAgent(), Beats()
    activities, review_input, reviews = await _world(agent, beats)
    ghost = RunReviewInput(change_id=str(uuid4()), agent_name=AGENT, run=1)

    with pytest.raises(ApplicationError) as error:
        await activities.record_review_infrastructure_failure(ghost)

    assert error.value.non_retryable is True
    assert reviews.persisted_events == []
