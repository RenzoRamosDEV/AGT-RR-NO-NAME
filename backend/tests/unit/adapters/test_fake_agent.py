from datetime import UTC, datetime
from uuid import uuid4

import pytest

from review_arena.adapters.agents.fake import FakeAgent
from review_arena.domain.change import Change, ChangeKind


def _make_change() -> Change:
    return Change.new(
        project_id=uuid4(),
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha="a" * 40,
        title="fix: algo",
        author="renzo",
        url="https://example.com",
        diff="diff --git a/x b/x",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )


async def test_two_named_fake_agents_are_independent() -> None:
    change = _make_change()
    agent_1 = FakeAgent("agent_1")
    agent_2 = FakeAgent("agent_2")

    result_1 = await agent_1.review(change)
    result_2 = await agent_2.review(change)

    assert "agent_1" in result_1.summary
    assert "agent_2" in result_2.summary


async def test_fake_agent_can_simulate_failure() -> None:
    agent = FakeAgent("agent_1", should_fail=True, failure_message="boom")

    with pytest.raises(RuntimeError, match="boom"):
        await agent.review(_make_change())
