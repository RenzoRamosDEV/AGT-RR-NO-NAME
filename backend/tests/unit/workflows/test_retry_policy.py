"""La política de reintentos de las activities de review es explícita y sale de un único sitio:
tres intentos, backoff exponencial y nunca más de un minuto entre dos (sin `maximum_interval`
Temporal esperaría hasta 100 × el intervalo inicial)."""

from __future__ import annotations

from datetime import timedelta

from duelo.application import review_timeouts
from duelo.workflows.review_change import RETRY


def test_the_workflow_retries_three_times_with_bounded_backoff() -> None:
    assert RETRY.maximum_attempts == 3
    assert RETRY.initial_interval == timedelta(seconds=1)
    assert RETRY.backoff_coefficient == 2.0
    assert RETRY.maximum_interval == timedelta(minutes=1)


def test_the_policy_is_built_from_the_shared_constants() -> None:
    assert RETRY.maximum_attempts == review_timeouts.RUN_REVIEW_RETRY_MAX_ATTEMPTS
    assert RETRY.initial_interval == review_timeouts.RUN_REVIEW_RETRY_INITIAL
    assert RETRY.backoff_coefficient == review_timeouts.RUN_REVIEW_RETRY_BACKOFF
    assert RETRY.maximum_interval == review_timeouts.RUN_REVIEW_RETRY_MAX_INTERVAL
