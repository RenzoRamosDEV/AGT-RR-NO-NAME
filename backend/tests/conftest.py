"""Configuración común de la suite: perfiles de hypothesis y marcadores por capa.

Los fixtures que necesitan infraestructura (Postgres/testcontainers) viven solo en
`tests/integration/conftest.py`, de modo que `tests/unit` no importa nada de `adapters`
ni requiere Docker (y mutmut puede aislar `domain/` y `application/`).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from hypothesis import HealthCheck, settings

settings.register_profile("dev", max_examples=100, deadline=None)
settings.register_profile(
    "ci",
    max_examples=200,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))

TESTS_DIR = Path(__file__).parent


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: sin I/O ni Docker (milisegundos)")
    config.addinivalue_line("markers", "integration: Postgres real y/o Temporal de test")
    config.addinivalue_line("markers", "e2e: flujo completo por HTTP con Postgres y Temporal")
    config.addinivalue_line("markers", "regression: fija un defecto ya corregido")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        relative = Path(str(item.path)).resolve().relative_to(TESTS_DIR)
        layer = relative.parts[0]
        if layer in {"unit", "integration", "e2e"}:
            item.add_marker(getattr(pytest.mark, layer))
