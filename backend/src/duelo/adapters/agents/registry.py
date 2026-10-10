"""Construye los agentes del worker a partir de los nombres de `AGENT_NAMES`.

`claude` y `codex` (sin distinguir mayúsculas) usan los CLI reales de la máquina; cualquier otro
nombre (`agent_1`, `agent_2`…, el valor por defecto) sigue siendo el agente de prueba, de modo que
el valor por defecto y la CI no lanzan nada real. La clave del diccionario es el nombre tal como
llega en `AGENT_NAMES`, que es el que pide el workflow.
"""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from duelo.adapters.agents.claude_cli import DEFAULT_MAX_BUDGET_USD, ClaudeCliAgent
from duelo.adapters.agents.cli_common import CommandRunner
from duelo.adapters.agents.codex_cli import CodexCliAgent
from duelo.adapters.agents.fake import FakeAgent
from duelo.adapters.subprocess_runner import run_command
from duelo.application.ports import ProjectPaths, ReviewAgent

CLAUDE = "claude"
CODEX = "codex"


@dataclass(frozen=True, slots=True)
class CliAgentConfig:
    timeout_seconds: float = 240.0
    max_concurrency: int = 2
    claude_bin: str | None = None
    codex_bin: str | None = None
    claude_model: str | None = None
    codex_model: str | None = None
    claude_max_budget_usd: float = DEFAULT_MAX_BUDGET_USD


def is_real_agent(name: str) -> bool:
    """¿Este nombre usa un CLI real? Lo necesita el worker para limitar la concurrencia."""
    return name.lower() in {CLAUDE, CODEX}


def build_agents(
    names: Sequence[str],
    config: CliAgentConfig,
    project_paths: ProjectPaths,
    *,
    runner: CommandRunner = run_command,
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, ReviewAgent]:
    # Un único semáforo para todos los CLI del worker: `claude` y `codex` comparten el tope.
    limiter = asyncio.Semaphore(config.max_concurrency)
    agents: dict[str, ReviewAgent] = {}
    for name in names:
        kind = name.lower()
        if kind == CLAUDE:
            agents[name] = ClaudeCliAgent(
                name,
                binary=config.claude_bin,
                model=config.claude_model,
                timeout_seconds=config.timeout_seconds,
                project_paths=project_paths,
                limiter=limiter,
                runner=runner,
                which=which,
                max_budget_usd=config.claude_max_budget_usd,
            )
        elif kind == CODEX:
            agents[name] = CodexCliAgent(
                name,
                binary=config.codex_bin,
                model=config.codex_model,
                timeout_seconds=config.timeout_seconds,
                project_paths=project_paths,
                limiter=limiter,
                runner=runner,
                which=which,
            )
        else:
            agents[name] = FakeAgent(name)
    return agents
