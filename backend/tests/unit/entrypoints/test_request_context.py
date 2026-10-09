"""`X-Request-ID` y access log estructurado."""

import json
import logging
from collections.abc import Iterable, Iterator

import httpx
import pytest

from duelo.entrypoints.api.middleware import access_logger, configure_access_logging
from tests.fakes.api import TOKEN, build_fake_api


def _client() -> httpx.AsyncClient:
    api = build_fake_api()
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


class _Lines:
    """Los registros de `caplog` cambian por fase del test: se leen siempre al momento."""

    def __init__(self, caplog: pytest.LogCaptureFixture) -> None:
        self._caplog = caplog

    def __iter__(self) -> Iterator[logging.LogRecord]:
        return iter(self._caplog.records)


@pytest.fixture
def access_lines(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> _Lines:
    # Las migraciones de los tests de integración (`fileConfig` de alembic) desactivan los loggers
    # ya creados: aquí se deja el logger tal como lo deja la app, con independencia del orden.
    monkeypatch.setattr(access_logger, "disabled", False)
    monkeypatch.setattr(access_logger, "propagate", True)
    caplog.set_level(logging.INFO, logger=access_logger.name)
    return _Lines(caplog)


def _entries(records: Iterable[logging.LogRecord]) -> list[dict[str, object]]:
    return [json.loads(r.getMessage()) for r in records if r.name == access_logger.name]


async def test_a_valid_incoming_request_id_is_echoed() -> None:
    async with _client() as client:
        response = await client.get("/health", headers={"X-Request-ID": "abc12345-trace.1_x"})

    assert response.headers["X-Request-ID"] == "abc12345-trace.1_x"


async def test_without_an_incoming_id_one_is_generated_per_request() -> None:
    async with _client() as client:
        first = await client.get("/health")
        second = await client.get("/health")

    ids = {first.headers["X-Request-ID"], second.headers["X-Request-ID"]}
    assert len(ids) == 2
    assert all(len(i) == 32 for i in ids)


@pytest.mark.parametrize(
    "incoming",
    [
        "short",  # < 8
        "x" * 65,  # > 64
        "con espacios en medio",
        "inyecta;DROP",
        "ñandú-12345678",  # fuera de ASCII
        "",
    ],
)
async def test_an_invalid_incoming_id_is_replaced_and_never_logged(
    access_lines: _Lines, incoming: str
) -> None:
    async with _client() as client:
        response = await client.get("/health", headers={"X-Request-ID": incoming.encode("latin-1")})

    generated = response.headers["X-Request-ID"]
    assert generated != incoming and len(generated) == 32
    assert incoming not in "".join(r.getMessage() for r in access_lines) or incoming == ""


async def test_the_access_log_is_one_json_line_with_the_route_template(
    access_lines: _Lines,
) -> None:
    async with _client() as client:
        response = await client.get(
            "/changes/00000000-0000-0000-0000-000000000000",
            headers={"X-Request-ID": "req-12345678"},
        )

    [entry] = _entries(access_lines)
    assert entry["request_id"] == "req-12345678"
    assert entry["method"] == "GET"
    assert entry["path"] == "/changes/{change_id}"  # plantilla, no el id real
    assert entry["status"] == response.status_code == 404
    assert isinstance(entry["duration_ms"], int | float) and entry["duration_ms"] >= 0


async def test_the_log_never_contains_query_strings_bodies_or_tokens(
    access_lines: _Lines,
) -> None:
    body = {"project": "acme/widgets", "ref": "r", "head_sha": "f" * 40, "diff": "SECRETO-EN-DIFF"}
    async with _client() as client:
        await client.get("/projects/acme/widgets/changes?q=busqueda-privada")
        await client.post("/ingest/commit", json=body, headers={"X-Ingest-Token": TOKEN})

    text = "".join(r.getMessage() for r in access_lines)
    assert "busqueda-privada" not in text
    assert "SECRETO-EN-DIFF" not in text
    assert TOKEN not in text
    assert {e["path"] for e in _entries(access_lines)} == {
        "/projects/{slug:path}/changes",
        "/ingest/commit",
    }


async def test_an_unknown_route_is_logged_as_unmatched(
    access_lines: _Lines,
) -> None:
    async with _client() as client:
        response = await client.get("/no-existe/secreto-123")

    [entry] = _entries(access_lines)
    assert response.status_code == entry["status"] == 404
    assert entry["path"] == "<unmatched>"
    assert "secreto-123" not in json.dumps(entry)


async def test_an_unhandled_error_is_logged_as_500(
    access_lines: _Lines,
) -> None:
    api = build_fake_api()

    async def boom() -> None:
        raise RuntimeError("fallo interno")

    api.app.add_api_route("/boom", boom)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    [entry] = _entries(access_lines)
    assert entry["status"] == 500 and entry["path"] == "/boom"


def test_configuring_the_access_log_is_idempotent_and_writes_bare_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(access_logger, "handlers", [])
    monkeypatch.setattr(access_logger, "disabled", False)  # ver `access_lines`
    monkeypatch.setattr(access_logger, "propagate", True)
    monkeypatch.setattr(access_logger, "level", logging.NOTSET)

    configure_access_logging()
    configure_access_logging()  # una segunda llamada no duplica la salida

    access_logger.info('{"request_id": "x"}')
    assert len(access_logger.handlers) == 1
    assert capsys.readouterr().out == '{"request_id": "x"}\n'
    assert access_logger.propagate is False  # no se duplica en el root
