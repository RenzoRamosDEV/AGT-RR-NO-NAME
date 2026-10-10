"""El worker registra los agentes por nombre y limita las activities concurrentes con CLI reales."""

from __future__ import annotations

import pytest
from temporalio.testing import WorkflowEnvironment

from duelo.config import WorkerSettings
from duelo.worker import build_workers, cli_agent_config

# Nada se conecta a la base de datos al construir los workers: el motor es perezoso.
DATABASE_URL = "postgresql+asyncpg://nadie:nadie@127.0.0.1:1/nada"


def _settings(**kw: object) -> WorkerSettings:
    return WorkerSettings(database_url=DATABASE_URL, **kw)  # type: ignore[arg-type]


def _agents_limit(env: WorkflowEnvironment, settings: WorkerSettings) -> int | None:
    _platform, agents = build_workers(env.client, settings)
    limit = agents.config()["max_concurrent_activities"]
    return limit


async def test_real_agents_limit_how_many_reviews_run_at_once(
    temporal_env: WorkflowEnvironment,
) -> None:
    limit = _agents_limit(
        temporal_env, _settings(agent_names=["claude", "codex"], agent_max_concurrency=3)
    )

    # Las reviews sobrantes esperan en la cola de Temporal, no dentro de la activity.
    assert limit == 3


@pytest.mark.parametrize("names", [["claude", "agent_2"], ["Codex"]])
async def test_a_single_real_agent_is_enough_to_limit(
    temporal_env: WorkflowEnvironment, names: list[str]
) -> None:
    assert _agents_limit(temporal_env, _settings(agent_names=names, agent_max_concurrency=1)) == 1


async def test_test_agents_alone_keep_the_default_unlimited_behaviour(
    temporal_env: WorkflowEnvironment,
) -> None:
    limit = _agents_limit(temporal_env, _settings(agent_names=["agent_1", "agent_2"]))

    assert limit is None  # sin tope propio: manda el valor por defecto del SDK


def test_the_cli_agent_configuration_is_taken_from_the_worker_settings() -> None:
    settings = _settings(
        agent_timeout_seconds=50,
        agent_max_concurrency=5,
        claude_bin="/c",
        codex_bin="/x",
        claude_model="m1",
        codex_model="m2",
        claude_max_budget_usd=0.4,
    )

    config = cli_agent_config(settings)

    assert (config.timeout_seconds, config.max_concurrency) == (50, 5)
    assert (config.claude_bin, config.codex_bin) == ("/c", "/x")
    assert (config.claude_model, config.codex_model) == ("m1", "m2")
    assert config.claude_max_budget_usd == 0.4
