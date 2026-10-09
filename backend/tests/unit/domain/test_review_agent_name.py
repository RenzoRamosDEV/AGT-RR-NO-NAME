"""Valores límite del nombre de agente (spec change-review)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from review_arena.domain.review import MAX_AGENT, Review, ReviewResult


def _succeeded(agent: str) -> Review:
    return Review.succeeded(
        change_id=uuid4(),
        agent=agent,
        run=1,
        result=ReviewResult(summary="ok", score=5, findings=()),
        raw_output=None,
        duration_ms=1,
        created_at=datetime.now(UTC),
    )


def _failed(agent: str) -> Review:
    return Review.failed(
        change_id=uuid4(),
        agent=agent,
        run=1,
        error="boom",
        duration_ms=None,
        created_at=datetime.now(UTC),
    )


@pytest.mark.parametrize("build", [_succeeded, _failed], ids=["succeeded", "failed"])
class TestAgentNameBoundaries:
    @pytest.mark.parametrize("length", [1, MAX_AGENT - 1, MAX_AGENT])
    def test_accepts_names_up_to_the_limit(self, build, length: int) -> None:
        assert build("a" * length).agent == "a" * length

    @pytest.mark.parametrize("name", ["", "a" * (MAX_AGENT + 1)], ids=["empty", "too-long"])
    def test_rejects_empty_and_over_limit_names(self, build, name: str) -> None:
        with pytest.raises(ValueError, match="agent"):
            build(name)


def test_agent_limit_is_50() -> None:
    assert MAX_AGENT == 50


class TestExactValidationMessages:
    def test_empty_agent(self) -> None:
        with pytest.raises(ValueError) as error:
            _succeeded("")
        assert str(error.value) == "agent no puede estar vacío"

    def test_too_long_agent(self) -> None:
        with pytest.raises(ValueError) as error:
            _failed("a" * (MAX_AGENT + 1))
        assert (
            str(error.value)
            == f"agent no puede superar {MAX_AGENT} caracteres (recibidos {MAX_AGENT + 1})"
        )
