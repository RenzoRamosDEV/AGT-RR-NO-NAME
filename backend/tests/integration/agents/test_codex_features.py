"""Vigila que una versión nueva de Codex no incorpore herramientas sin que alguien las revise.

`codex features list` NO llama al modelo: no consume suscripción, así que corre con la suite normal
de quien tenga `codex` instalado (en la CI no lo hay y se salta). Si falla, el nombre de la función
nueva aparece en el mensaje: revísala y clasifícala en `codex_cli.py` como desactivada
(`DISABLED_FEATURES`: ejecuta código, lee el disco, lanza subagentes, red, plugins o MCP) o como
revisada y permitida (`REVIEWED_ALLOWED_FEATURES`, con su motivo).
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from duelo.adapters.agents.codex_cli import unreviewed_features


@pytest.mark.skipif(shutil.which("codex") is None, reason="el CLI de codex no está instalado")
def test_every_enabled_feature_of_the_installed_codex_is_classified() -> None:
    result = subprocess.run(
        ["codex", "features", "list"], capture_output=True, text=True, timeout=60, check=True
    )

    assert result.stdout.strip(), "`codex features list` no devolvió nada: ¿cambió el formato?"
    assert unreviewed_features(result.stdout) == [], (
        "Funciones habilitadas de Codex sin clasificar: revísalas y añádelas a "
        "DISABLED_FEATURES o a REVIEWED_ALLOWED_FEATURES en adapters/agents/codex_cli.py"
    )
