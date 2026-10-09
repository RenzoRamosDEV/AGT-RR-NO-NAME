"""Tabla de decisión de la activity `run_review`, llamada directamente (sin Temporal).

| agente conocido | change existe | el agente lanza | resultado                              |
|-----------------|---------------|-----------------|----------------------------------------|
| no              | (da igual)    | (da igual)      | ApplicationError no reintentable       |
| sí              | no            | (da igual)      | ApplicationError no reintentable       |
| sí              | sí            | no              | Review completed + evento completed    |
| sí              | sí            | sí              | Review failed (con el error) + evento  |

La precedencia importa: un agente desconocido gana a un change inexistente.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from temporalio.exceptions import ApplicationError

from duelo.adapters.agents.fake import FakeAgent
from duelo.application.ingest_change import ingest_change
from duelo.domain.change import ChangeKind
from duelo.domain.events import ReviewCompleted, ReviewFailed
from duelo.workflows.activities import ReviewActivities
from duelo.workflows.dto import RunReviewInput
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.review_repository import FakeReviewRepository
from tests.fakes.session import FakeSessionFactory

KNOWN = "agent_ok"


async def _scenario(*, agent_known: bool, change_exists: bool, agent_raises: bool):
    changes = FakeChangeRepository()
    reviews = FakeReviewRepository()
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
    agents = {KNOWN: FakeAgent(KNOWN, should_fail=agent_raises, failure_message="el agente fallo")}
    activities = ReviewActivities(
        session_factory=FakeSessionFactory(),  # type: ignore[arg-type]
        change_repository=lambda _session: changes,
        review_repository=lambda _session: reviews,
        agents=agents,  # type: ignore[arg-type]
    )
    review_input = RunReviewInput(
        change_id=str(change.id if change_exists else uuid4()),
        agent_name=KNOWN if agent_known else "fantasma",
        run=2,
    )
    return activities, review_input, reviews, change


@pytest.mark.parametrize("change_exists", [True, False], ids=["change-existe", "change-no-existe"])
@pytest.mark.parametrize("agent_raises", [True, False], ids=["agente-lanza", "agente-ok"])
async def test_unknown_agent_is_a_non_retryable_error_whatever_the_rest(
    change_exists: bool, agent_raises: bool
) -> None:
    activities, review_input, reviews, _ = await _scenario(
        agent_known=False, change_exists=change_exists, agent_raises=agent_raises
    )

    with pytest.raises(ApplicationError) as error:
        await activities.run_review(review_input)

    assert error.value.non_retryable is True
    assert "Agente desconocido: fantasma" in str(error.value)
    assert reviews.persisted_events == []


@pytest.mark.parametrize("agent_raises", [True, False], ids=["agente-lanza", "agente-ok"])
async def test_missing_change_is_a_non_retryable_error(agent_raises: bool) -> None:
    activities, review_input, reviews, _ = await _scenario(
        agent_known=True, change_exists=False, agent_raises=agent_raises
    )

    with pytest.raises(ApplicationError) as error:
        await activities.run_review(review_input)

    assert error.value.non_retryable is True
    assert f"Change {review_input.change_id} no existe" in str(error.value)
    assert reviews.persisted_events == []


async def test_known_agent_and_existing_change_persists_a_completed_review() -> None:
    activities, review_input, reviews, change = await _scenario(
        agent_known=True, change_exists=True, agent_raises=False
    )
    before = datetime.now(UTC)

    result = await activities.run_review(review_input)

    assert result.status == "completed"
    (event,) = reviews.persisted_events
    assert isinstance(event, ReviewCompleted)
    assert (event.review_id.hex, event.change_id, event.agent) == (
        result.review_id.replace("-", ""),
        change.id,
        KNOWN,
    )
    stored = next(iter(reviews._by_natural_key.values()))
    assert stored.run == 2
    assert stored.created_at >= before
    assert stored.duration_ms is not None and stored.duration_ms >= 0


async def test_agent_that_raises_persists_a_failed_review_with_its_error() -> None:
    activities, review_input, reviews, change = await _scenario(
        agent_known=True, change_exists=True, agent_raises=True
    )

    result = await activities.run_review(review_input)

    assert result.status == "failed"
    (event,) = reviews.persisted_events
    assert isinstance(event, ReviewFailed)
    assert (event.change_id, event.agent, event.error) == (change.id, KNOWN, "el agente fallo")
    stored = next(iter(reviews._by_natural_key.values()))
    assert (stored.status.value, stored.error, stored.run) == ("failed", "el agente fallo", 2)
    assert stored.duration_ms is not None and stored.duration_ms >= 0
