"""Contrato de la API: snapshot del OpenAPI (cambiarlo es una decisión explícita) y
fuzzing de contrato con schemathesis contra la app ASGI con fakes."""

from __future__ import annotations

import json
from pathlib import Path

import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.specs.openapi.checks import allow_header_conformance, positive_data_acceptance

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

    # El cursor del canal es opaco: para el esquema es un string cualquiera, pero solo vale el
    # que devolvió el propio servidor; rechazar otro con 422 es el contrato (se prueba aparte).
    opaque_cursor = (case.query or {}).get("cursor") is not None
    # Starlette responde el 405 de una ruta con varios métodos (`GET` y `POST /projects`, en
    # routers distintos) listando en `Allow` solo el de la primera ruta que casa por ruta: es una
    # limitación del framework y no del contrato, así que no se exige esa cabecera.
    excluded = [allow_header_conformance]
    if opaque_cursor:
        excluded.append(positive_data_acceptance)
    case.call_and_validate(excluded_checks=excluded)
