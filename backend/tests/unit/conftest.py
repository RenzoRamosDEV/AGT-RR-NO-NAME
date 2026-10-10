"""Aislamiento de git para los tests que crean repos reales: sin la configuración global ni del
sistema de quien ejecuta la suite (un `core.hooksPath` o un `init.defaultBranch` propios la
alterarían) y con una identidad fija."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _isolated_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "Ana Pérez")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "ana@example.com")
    # Que ningún test lea o escriba el hook.env real del usuario.
    monkeypatch.delenv("INGEST_URL", raising=False)
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
