"""Contrato de la API: snapshot del OpenAPI (cambiarlo es una decisión explícita) y
fuzzing de contrato con schemathesis contra la app ASGI con fakes."""

from __future__ import annotations

import json
from pathlib import Path

import schemathesis
from hypothesis import HealthCheck, settings

from tests.fakes.api import TOKEN, build_fake_api

SNAPSHOT = Path(__file__).resolve().parents[4] / "docs" / "openapi.json"


def _app():
    return build_fake_api().app


def test_openapi_matches_the_committed_snapshot() -> None:
    """Si falla: revisa el cambio de contrato y regenera con `just openapi`."""
    current = json.dumps(_app().openapi(), indent=2, sort_keys=True) + "\n"

    assert SNAPSHOT.read_text() == current


schema = schemathesis.openapi.from_asgi("/openapi.json", _app())


@schema.parametrize()
@settings(max_examples=40, deadline=None, suppress_health_check=list(HealthCheck))
def test_api_honours_its_own_contract(case: schemathesis.Case) -> None:
    case.headers = {**(case.headers or {}), "X-Ingest-Token": TOKEN}

    case.call_and_validate()
