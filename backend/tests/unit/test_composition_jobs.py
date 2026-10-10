"""Qué tareas de fondo arranca la composición real según la configuración."""

from __future__ import annotations

import pytest

from duelo.composition import build_api_dependencies
from duelo.config import Settings


def _settings(monkeypatch: pytest.MonkeyPatch, **values: object) -> Settings:
    for name in (
        "LOCAL_PROJECTS_ENABLED",
        "PR_SYNC_INTERVAL_SECONDS",
        "REACHABILITY_SWEEP_INTERVAL_SECONDS",
        "REACHABILITY_WINDOW_COMMITS",
    ):
        monkeypatch.delenv(name, raising=False)
    return Settings(ingest_token="t", **values)  # type: ignore[arg-type]


def test_without_local_projects_there_are_no_background_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El barrido solo tiene sentido con carpetas locales: sin ellas ni se arranca."""
    deps = build_api_dependencies(_settings(monkeypatch, reachability_sweep_interval_seconds=15))

    assert list(deps.background_jobs) == []


def test_with_local_projects_the_reachability_sweep_runs_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deps = build_api_dependencies(_settings(monkeypatch, local_projects_enabled=True))

    assert len(deps.background_jobs) == 1  # el barrido (la sincronización de PRs está apagada)


def test_the_sweep_can_be_turned_off_with_a_zero_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deps = build_api_dependencies(
        _settings(monkeypatch, local_projects_enabled=True, reachability_sweep_interval_seconds=0)
    )

    assert list(deps.background_jobs) == []


def test_the_pr_sync_and_the_sweep_are_independent_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deps = build_api_dependencies(
        _settings(monkeypatch, local_projects_enabled=True, pr_sync_interval_seconds=300)
    )

    assert len(deps.background_jobs) == 2
