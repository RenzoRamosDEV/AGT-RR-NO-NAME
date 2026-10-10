from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from duelo.adapters.agents.claude_cli import ClaudeCliAgent
from duelo.adapters.agents.codex_cli import CodexCliAgent
from duelo.adapters.agents.fake import FakeAgent
from duelo.adapters.agents.registry import CliAgentConfig, build_agents, is_real_agent
from tests.fakes.cli_runner import (
    FakeProjectPaths,
    FakeRunner,
    RunnerCall,
    make_change,
    option_value,
)

CLAUDE_JSON = json.dumps(
    {"is_error": False, "structured_output": {"summary": "ok", "score": 6, "findings": []}}
)


def _codex_writes(call: RunnerCall) -> None:
    Path(option_value(call.argv, "-o")).write_text(
        json.dumps({"summary": "ok", "score": 6, "findings": []})
    )


def _build(names: list[str], config: CliAgentConfig | None = None, **kw: Any) -> Any:
    return build_agents(
        names,
        config or CliAgentConfig(),
        FakeProjectPaths(),
        which=lambda name: f"/usr/bin/{name}",
        **kw,
    )


def test_the_default_names_keep_using_the_fake_agent() -> None:
    agents = _build(["agent_1", "agent_2"])

    assert set(agents) == {"agent_1", "agent_2"}
    assert all(isinstance(agent, FakeAgent) for agent in agents.values())


def test_claude_and_codex_use_the_real_cli_agents() -> None:
    agents = _build(["claude", "codex"])

    assert isinstance(agents["claude"], ClaudeCliAgent)
    assert isinstance(agents["codex"], CodexCliAgent)
    assert (agents["claude"].name, agents["codex"].name) == ("claude", "codex")


@pytest.mark.parametrize("name", ["Claude", "CLAUDE", "cLaUdE"])
def test_names_are_matched_without_distinguishing_case_but_keep_their_spelling(name: str) -> None:
    agents = _build([name])

    assert isinstance(agents[name], ClaudeCliAgent)
    assert agents[name].name == name  # el workflow pide el nombre tal cual llega en AGENT_NAMES


def test_real_and_test_agents_can_be_mixed() -> None:
    agents = _build(["claude", "agent_2", "Codex"])

    assert [type(a).__name__ for a in agents.values()] == [
        "ClaudeCliAgent",
        "FakeAgent",
        "CodexCliAgent",
    ]


@pytest.mark.parametrize(
    ("name", "real"),
    [("claude", True), ("Codex", True), ("CODEX", True), ("agent_1", False), ("claudio", False)],
)
def test_is_real_agent(name: str, real: bool) -> None:
    assert is_real_agent(name) is real


async def test_the_configuration_reaches_each_cli() -> None:
    config = CliAgentConfig(
        timeout_seconds=33.0,
        claude_bin=None,
        claude_model="opus",
        codex_model="gpt-x",
        claude_max_budget_usd=0.25,
    )
    claude_runner, codex_runner = FakeRunner(stdout=CLAUDE_JSON), FakeRunner(on_call=_codex_writes)
    claude = build_agents(
        ["claude"], config, FakeProjectPaths(), runner=claude_runner, which=lambda _n: "/c"
    )["claude"]
    codex = build_agents(
        ["codex"], config, FakeProjectPaths(), runner=codex_runner, which=lambda _n: "/x"
    )["codex"]

    await claude.review(make_change())
    await codex.review(make_change())

    (claude_call,) = claude_runner.calls
    (codex_call,) = codex_runner.calls
    assert claude_call.timeout == codex_call.timeout == 33.0
    assert option_value(claude_call.argv, "--model") == "opus"
    assert option_value(claude_call.argv, "--max-budget-usd") == "0.25"
    assert option_value(codex_call.argv, "-m") == "gpt-x"


async def test_claude_and_codex_share_one_concurrency_limit() -> None:
    running = 0
    peak = 0

    def answer_like_codex(call: RunnerCall) -> None:
        if "-o" in call.argv:
            _codex_writes(call)

    class SlowRunner(FakeRunner):
        async def __call__(self, *args: Any, **kwargs: Any) -> Any:
            nonlocal running, peak
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.05)
            running -= 1
            return await super().__call__(*args, **kwargs)

    runner = SlowRunner(stdout=CLAUDE_JSON, on_call=answer_like_codex)
    agents = build_agents(
        ["claude", "codex"],
        CliAgentConfig(max_concurrency=1),
        FakeProjectPaths(),
        runner=runner,
        which=lambda _n: "/x",
    )

    await asyncio.gather(
        agents["claude"].review(make_change()), agents["codex"].review(make_change())
    )

    assert len(runner.calls) == 2
    assert peak == 1  # un solo tope compartido por los dos CLI
