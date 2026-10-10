"""Revisión de un diff diminuto con los CLI REALES de Claude Code y Codex.

NO corren por defecto ni en la CI: consumen la suscripción del usuario y necesitan los CLI
instalados y con la sesión iniciada. Para ejecutarlos:

    RUN_CLI_AGENT_TESTS=1 uv run pytest tests/integration/agents -m cli_agents --no-cov -s

Comprueban que el formato real de salida de cada CLI sigue encajando con los parsers (no el
criterio del modelo, que puede variar).
"""

from __future__ import annotations

import os
import shutil

import pytest

from duelo.adapters.agents.claude_cli import ClaudeCliAgent
from duelo.adapters.agents.codex_cli import CodexCliAgent
from duelo.adapters.agents.review_payload import SEVERITIES
from duelo.domain.review import ReviewResult
from tests.fakes.cli_runner import make_change

pytestmark = [
    pytest.mark.cli_agents,
    pytest.mark.skipif(
        os.environ.get("RUN_CLI_AGENT_TESTS") != "1",
        reason="consume suscripción: define RUN_CLI_AGENT_TESTS=1 para ejecutarlo",
    ),
]

TINY_DIFF = """--- a/a.py
+++ b/a.py
@@ -1,2 +1,3 @@
 def div(a, b):
-    return a / b
+    return a / (b - 0)
+print(div(1, 0))
"""


def _assert_a_real_review(result: ReviewResult) -> None:
    assert result.summary.strip()
    assert result.score is not None and 0 <= result.score <= 10
    for finding in result.findings:
        assert finding.severity in SEVERITIES
        assert finding.message.strip()
        assert finding.line >= 0


@pytest.mark.skipif(shutil.which("claude") is None, reason="el CLI de claude no está instalado")
async def test_claude_reviews_a_tiny_diff() -> None:
    agent = ClaudeCliAgent(
        "claude", binary=None, model=None, timeout_seconds=170, project_paths=None
    )

    _assert_a_real_review(await agent.review(make_change(diff=TINY_DIFF)))


@pytest.mark.skipif(shutil.which("codex") is None, reason="el CLI de codex no está instalado")
async def test_codex_reviews_a_tiny_diff() -> None:
    agent = CodexCliAgent("codex", binary=None, model=None, timeout_seconds=170, project_paths=None)

    _assert_a_real_review(await agent.review(make_change(diff=TINY_DIFF)))
