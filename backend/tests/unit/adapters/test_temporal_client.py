"""`LazyTemporalClient` conecta en el primer uso y en el namespace configurado."""

from __future__ import annotations

from typing import Any

import pytest
from temporalio.client import Client

from duelo.adapters.orchestration.temporal_client import LazyTemporalClient


@pytest.fixture
def connections(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def fake_connect(address: str, **kwargs: Any) -> object:
        calls.append({"address": address, **kwargs})
        return object()

    monkeypatch.setattr(Client, "connect", fake_connect)
    return calls


async def test_connects_to_the_configured_namespace(connections: list[dict[str, Any]]) -> None:
    client = LazyTemporalClient("temporal:7233", "staging")

    await client.get()

    assert connections == [{"address": "temporal:7233", "namespace": "staging"}]


async def test_defaults_to_the_default_namespace(connections: list[dict[str, Any]]) -> None:
    await LazyTemporalClient("localhost:7233").get()

    assert connections[0]["namespace"] == "default"


async def test_connects_once_and_reuses_the_client(connections: list[dict[str, Any]]) -> None:
    client = LazyTemporalClient("localhost:7233")

    first = await client.get()
    second = await client.get()

    assert first is second
    assert len(connections) == 1
