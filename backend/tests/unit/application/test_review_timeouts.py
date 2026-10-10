from __future__ import annotations

from datetime import timedelta

from duelo.application.review_timeouts import (
    AGENT_TIMEOUT_MARGIN,
    MAX_AGENT_TIMEOUT_SECONDS,
    RUN_REVIEW_START_TO_CLOSE,
)


def test_the_activity_has_five_minutes_and_the_agent_keeps_thirty_seconds_of_margin() -> None:
    assert RUN_REVIEW_START_TO_CLOSE == timedelta(minutes=5)
    assert AGENT_TIMEOUT_MARGIN == timedelta(seconds=30)
    assert MAX_AGENT_TIMEOUT_SECONDS == 270.0


def test_the_ceiling_is_derived_from_the_activity_timeout_and_the_margin() -> None:
    assert (
        MAX_AGENT_TIMEOUT_SECONDS
        == (RUN_REVIEW_START_TO_CLOSE - AGENT_TIMEOUT_MARGIN).total_seconds()
    )
    assert MAX_AGENT_TIMEOUT_SECONDS < RUN_REVIEW_START_TO_CLOSE.total_seconds()
