"""POST /projects, DELETE /projects/{slug} y POST /projects/{slug}/sync-prs."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from duelo.adapters.ratelimit.in_memory import InMemoryRateLimiter
from duelo.application.ports import RepoInfo
from duelo.config import Settings
from duelo.entrypoints.api.app import create_app
from tests.fakes.api import TOKEN, FakeApi, build_fake_api
from tests.fakes.local_projects import (
    FakeGithubPrSource,
    FakeGitRepository,
    FakeHookInstaller,
    pull_request,
)
from tests.fakes.review_starter import FakeReviewStarter

HEADERS = {"X-Ingest-Token": TOKEN}
ROOT = "/home/u/widgets"
SLUG = "acme/widgets-local"  # distinto del proyecto sin carpeta que ya crea el fake


def _client(api: FakeApi) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://test",
    )


def _local_api(**kwargs: Any) -> FakeApi:
    kwargs.setdefault(
        "git",
        FakeGitRepository(RepoInfo(root=ROOT, remote_url="git@github.com:acme/widgets-local.git")),
    )
    return build_fake_api(local_projects=True, **kwargs)


# --- desactivado por defecto -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        ("POST", "/projects", {"path": ROOT}),
        ("DELETE", "/projects/acme/widgets", None),
        ("POST", "/projects/acme/widgets/sync-prs", None),
    ],
)
@pytest.mark.parametrize("headers", [HEADERS, {}, {"X-Ingest-Token": "mal"}])
async def test_when_disabled_every_request_is_404_with_or_without_token(
    method: str, url: str, body: dict[str, str] | None, headers: dict[str, str]
) -> None:
    api = build_fake_api()  # LOCAL_PROJECTS_ENABLED apagado por defecto
    async with _client(api) as client:
        response = await client.request(method, url, json=body, headers=headers)

    assert response.status_code == 404
    assert api.hooks.installed == [] and api.git.inspected == []
    assert [p.slug for p in await api.projects.list_all()] == ["acme/widgets"]


def test_the_feature_flag_defaults_to_off() -> None:
    assert Settings(ingest_token="t").local_projects_enabled is False  # type: ignore[call-arg]


async def test_enabled_in_settings_but_not_wired_is_still_404() -> None:
    api = build_fake_api(local_projects=True)
    api.app.state.dependencies.add_local_project = None
    async with _client(api) as client:
        response = await client.post("/projects", json={"path": ROOT}, headers=HEADERS)

    assert response.status_code == 404


# --- autenticación -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        ("POST", "/projects", {"path": ROOT}),
        ("DELETE", "/projects/acme/widgets", None),
        ("POST", "/projects/acme/widgets/sync-prs", None),
    ],
)
@pytest.mark.parametrize("headers", [{}, {"X-Ingest-Token": "mal"}])
async def test_enabled_requires_the_ingest_token(
    method: str, url: str, body: dict[str, str] | None, headers: dict[str, str]
) -> None:
    api = _local_api()
    async with _client(api) as client:
        response = await client.request(method, url, json=body, headers=headers)

    assert response.status_code == 401
    assert api.hooks.installed == [] and api.git.inspected == []


# --- POST /projects ----------------------------------------------------------------------------


async def test_adding_a_project_returns_201_and_it_shows_up_in_the_list() -> None:
    api = _local_api()
    async with _client(api) as client:
        response = await client.post("/projects", json={"path": ROOT}, headers=HEADERS)
        listing = (await client.get("/projects")).json()

    assert response.status_code == 201
    body = response.json()
    assert {k: v for k, v in body.items() if k != "id"} == {
        "slug": SLUG,
        "path": ROOT,
        "hooks_installed": True,
        "github": True,
    }
    assert api.hooks.installed == [(ROOT, SLUG)]
    assert {k: v for k, v in listing[1].items() if k != "id"} == {
        "slug": SLUG,
        "path": ROOT,
        "hooks_installed": True,
        "github": True,
    }


async def test_a_repeated_project_is_409_and_hooks_are_not_installed_twice() -> None:
    api = _local_api()
    async with _client(api) as client:
        await client.post("/projects", json={"path": ROOT}, headers=HEADERS)
        again = await client.post("/projects", json={"path": ROOT}, headers=HEADERS)

    assert again.status_code == 409
    assert len(api.hooks.installed) == 1


async def test_an_invalid_repository_is_422_with_the_reason_and_registers_nothing() -> None:
    api = _local_api(git=FakeGitRepository(error="La ruta no es un repositorio git"))
    async with _client(api) as client:
        response = await client.post("/projects", json={"path": "/tmp/x"}, headers=HEADERS)

    assert response.status_code == 422
    assert response.json() == {"detail": "La ruta no es un repositorio git"}
    assert [p.slug for p in await api.projects.list_all()] == ["acme/widgets"]


async def test_a_hook_that_cannot_be_installed_is_422_and_leaves_no_project() -> None:
    api = _local_api(hooks=FakeHookInstaller(install_error="El hook post-commit no es de shell"))
    async with _client(api) as client:
        response = await client.post("/projects", json={"path": ROOT}, headers=HEADERS)

    assert response.status_code == 422
    assert "no es de shell" in response.json()["detail"]
    assert [p.slug for p in await api.projects.list_all()] == ["acme/widgets"]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"path": ""},
        {"path": 5},
        {"path": "a\x00b"},
        {"path": "x" * 5000},
        {"path": "/a", "x": 1},
    ],
)
async def test_a_malformed_body_is_422_before_anything_is_inspected(body: dict[str, Any]) -> None:
    api = _local_api()
    async with _client(api) as client:
        response = await client.post("/projects", json=body, headers=HEADERS)

    assert response.status_code == 422
    assert api.git.inspected == []


# --- DELETE /projects/{slug} -------------------------------------------------------------------


async def test_deleting_a_project_removes_it_and_uninstalls_its_hooks() -> None:
    api = _local_api()
    async with _client(api) as client:
        await client.post("/projects", json={"path": ROOT}, headers=HEADERS)
        response = await client.delete(f"/projects/{SLUG}", headers=HEADERS)
        listing = (await client.get("/projects")).json()

    assert response.status_code == 204 and response.content == b""
    assert api.hooks.uninstalled == [ROOT]
    assert [p["slug"] for p in listing] == ["acme/widgets"]


async def test_deleting_an_unknown_project_is_404() -> None:
    api = _local_api()
    async with _client(api) as client:
        response = await client.delete("/projects/no/existe", headers=HEADERS)

    assert response.status_code == 404


# --- POST /projects/{slug}/sync-prs ------------------------------------------------------------


async def test_sync_registers_the_open_prs_and_reports_counts() -> None:
    api = _local_api(github=FakeGithubPrSource([pull_request(1), pull_request(2)]))
    async with _client(api) as client:
        await client.post("/projects", json={"path": ROOT}, headers=HEADERS)
        first = await client.post(f"/projects/{SLUG}/sync-prs", headers=HEADERS)
        second = await client.post(f"/projects/{SLUG}/sync-prs", headers=HEADERS)
        channel = (await client.get(f"/projects/{SLUG}/changes?kind=pr")).json()

    assert (first.status_code, first.json()) == (200, {"synced": 2, "created": 2})
    assert second.json() == {"synced": 2, "created": 0}
    assert sorted(c["title"] for c in channel["items"]) == ["feat: pr 1", "feat: pr 2"]
    assert api.github.queried == [ROOT, ROOT]


@pytest.mark.parametrize(
    ("setup", "status", "fragment"),
    [
        ("unknown", 404, "Proyecto desconocido"),
        ("no-folder", 409, "no tiene carpeta local"),
        ("gh-down", 503, "gh no ha iniciado sesión"),
        ("temporal-down", 503, "No se pudo arrancar la review"),
    ],
)
async def test_sync_failures_map_to_their_status(setup: str, status: int, fragment: str) -> None:
    github = FakeGithubPrSource(
        [pull_request(1)],
        unavailable="gh no ha iniciado sesión" if setup == "gh-down" else None,
    )
    api = _local_api(
        github=github,
        starter=FakeReviewStarter(fail=True) if setup == "temporal-down" else None,
    )
    slug = {"unknown": "no/existe", "no-folder": "acme/widgets"}.get(setup, SLUG)
    async with _client(api) as client:
        await client.post("/projects", json={"path": ROOT}, headers=HEADERS)
        response = await client.post(f"/projects/{slug}/sync-prs", headers=HEADERS)

    assert response.status_code == status
    assert fragment in response.json()["detail"]


# --- límite de peticiones ----------------------------------------------------------------------


async def test_the_endpoints_share_the_rate_limit_and_it_comes_after_the_enabled_check() -> None:
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60, clock=lambda: 0.0)
    api = _local_api(rate_limiter=limiter)
    async with _client(api) as client:
        codes = [
            (await client.delete("/projects/no/existe", headers=HEADERS)).status_code
            for _ in range(4)
        ]
        retry_after = (await client.delete("/projects/x/y", headers=HEADERS)).headers["Retry-After"]

    assert codes == [404, 404, 429, 429] and int(retry_after) >= 1


async def test_a_disabled_feature_does_not_spend_the_rate_limit() -> None:
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60, clock=lambda: 0.0)
    api = build_fake_api(rate_limiter=limiter)
    async with _client(api) as client:
        codes = [
            (await client.post("/projects", json={"path": ROOT}, headers=HEADERS)).status_code
            for _ in range(3)
        ]

    assert codes == [404, 404, 404]


def test_the_app_is_built_with_the_routes_even_when_disabled() -> None:
    # Documentadas siempre en el OpenAPI: el 404 es de ejecución, no de contrato.
    paths = create_app(
        Settings(ingest_token="t"),  # type: ignore[call-arg]
        build_fake_api().app.state.dependencies,
    ).openapi()["paths"]

    assert set(paths["/projects"]) == {"get", "post"}
    assert "delete" in paths["/projects/{slug}"] and "post" in paths["/projects/{slug}/sync-prs"]
