"""CORS: solo para los orígenes configurados, sin credenciales."""

import httpx

from tests.fakes.api import build_fake_api

ALLOWED = "http://localhost:5173"


def _client(**kwargs: object) -> httpx.AsyncClient:
    api = build_fake_api(**kwargs)  # type: ignore[arg-type]
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


async def test_an_allowed_origin_gets_the_cors_headers() -> None:
    async with _client(allowed_origins=[ALLOWED]) as client:
        response = await client.get("/projects", headers={"Origin": ALLOWED})

    assert response.headers["access-control-allow-origin"] == ALLOWED
    # Sin credenciales y exponiendo lo que el frontend necesita leer.
    assert "access-control-allow-credentials" not in response.headers
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]
    assert "Retry-After" in response.headers["access-control-expose-headers"]


async def test_a_preflight_from_an_allowed_origin_lists_methods_and_headers() -> None:
    async with _client(allowed_origins=[ALLOWED]) as client:
        response = await client.options(
            "/changes/00000000-0000-0000-0000-000000000000/retry",
            headers={
                "Origin": ALLOWED,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "x-ingest-token, content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert response.headers["access-control-allow-methods"] == "GET, POST, DELETE"
    assert "X-Ingest-Token" in response.headers["access-control-allow-headers"]
    assert "X-Request-ID" in response.headers  # el preflight también lo lleva


async def test_an_unlisted_origin_gets_no_cors_headers() -> None:
    async with _client(allowed_origins=[ALLOWED]) as client:
        response = await client.get("/projects", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers


async def test_the_operator_token_header_is_not_allowed_from_a_browser() -> None:
    async with _client(allowed_origins=[ALLOWED]) as client:
        response = await client.options(
            "/reviews/00000000-0000-0000-0000-000000000000/raw-output",
            headers={
                "Origin": ALLOWED,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-operator-token",
            },
        )

    assert response.status_code == 400  # la salida cruda es para el operador, no para el navegador


async def test_without_configured_origins_there_is_no_cors_at_all() -> None:
    async with _client() as client:
        simple = await client.get("/projects", headers={"Origin": ALLOWED})
        preflight = await client.options(
            "/projects",
            headers={"Origin": ALLOWED, "Access-Control-Request-Method": "GET"},
        )

    assert not [h for h in simple.headers if h.startswith("access-control")]
    assert not [h for h in preflight.headers if h.startswith("access-control")]
    assert preflight.status_code == 405
