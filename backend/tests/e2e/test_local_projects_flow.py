"""Proyectos locales de punta a punta: API real por HTTP (uvicorn) + Postgres real + Temporal de
test + workers, repos git reales y los hooks reales que instala la API.

El criterio de «hecho»: añado una carpeta, hago un commit con git y el change aparece en el canal
con sus reviews, sin llamar yo a ninguna API de ingesta.
"""

from __future__ import annotations

import asyncio
import os
import socket
import stat
import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import uvicorn
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio.testing import WorkflowEnvironment

from duelo.composition import build_api_dependencies
from duelo.config import Settings
from duelo.entrypoints.api.app import create_app
from tests.e2e.test_ingest_flow import HEADERS, TOKEN, _until, _workers


@pytest.fixture(autouse=True)
def _git_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "Ana Pérez")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "ana@example.com")
    # El hook lee el token de aquí (lo escribe la API al dar de alta el proyecto).
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("INGEST_URL", raising=False)
    monkeypatch.delenv("INGEST_TOKEN", raising=False)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@asynccontextmanager
async def _server(
    database_url: str, temporal_address: str, tmp_path: Path
) -> AsyncIterator[httpx.AsyncClient]:
    port = _free_port()
    settings = Settings(
        ingest_token=TOKEN,
        database_url=database_url,
        temporal_address=temporal_address,
        local_projects_enabled=True,
        ingest_url=f"http://127.0.0.1:{port}",
        hook_env_path=str(tmp_path / "xdg" / "duelo" / "hook.env"),
    )
    deps = build_api_dependencies(settings)
    server = uvicorn.Server(
        uvicorn.Config(create_app(settings, deps), host="127.0.0.1", port=port, log_level="warning")
    )
    task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            break
        await asyncio.sleep(0.1)
    assert server.started, "uvicorn no arrancó"
    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
            yield client
    finally:
        server.should_exit = True
        await task


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def _new_repo(tmp_path: Path, name: str) -> tuple[Path, str]:
    slug = f"acme/{name}-{uuid4().hex[:8]}"
    repo = tmp_path / name
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    _git(repo, "remote", "add", "origin", f"git@github.com:{slug}.git")
    return repo.resolve(), slug


async def _commit(repo: Path, name: str, message: str) -> str:
    def run() -> str:
        (repo / name).write_text(f"{message}\n")
        _git(repo, "add", name)
        _git(repo, "commit", "-q", "-m", message)
        return _git(repo, "rev-parse", "HEAD").strip()

    return await asyncio.to_thread(run)


async def _channel(client: httpx.AsyncClient, slug: str) -> list[dict]:
    return (await client.get(f"/projects/{slug}/changes")).json()["items"]


async def test_add_a_folder_then_commit_and_push_show_up_in_the_channel_with_reviews(
    temporal_env: WorkflowEnvironment, database_url: str, tmp_path: Path
) -> None:
    repo, slug = _new_repo(tmp_path, "widgets")
    bare = tmp_path / "remoto.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    await asyncio.to_thread(_git, repo, "config", "remote.origin.pushurl", str(bare))
    target = temporal_env.client.service_client.config.target_host

    async with _workers(temporal_env, database_url), _server(database_url, target, tmp_path) as api:
        added = await api.post("/projects", json={"path": str(repo)}, headers=HEADERS)
        assert added.status_code == 201, added.text
        assert (added.json()["slug"], added.json()["github"]) == (slug, True)
        assert (repo / ".git" / "hooks" / "post-commit").stat().st_mode & stat.S_IXUSR

        listed = (await api.get("/projects")).json()
        assert [p for p in listed if p["slug"] == slug] == [
            {**added.json()}  # el mismo registro, con ruta y hooks
        ]

        # 1) un commit con git aparece solo, con sus reviews
        sha = await _commit(repo, "app.py", "feat: primer commit")

        async def arrived() -> bool:
            return any(c["head_sha"] == sha for c in await _channel(api, slug))

        await _until(arrived)
        (change,) = (c for c in await _channel(api, slug) if c["head_sha"] == sha)
        assert (change["kind"], change["ref"], change["title"], change["author"]) == (
            "commit",
            "main",
            "feat: primer commit",
            "Ana Pérez",
        )
        assert change["diff_summary"]["files"] == [
            {"path": "app.py", "additions": 1, "deletions": 0}
        ]

        async def reviewed() -> bool:
            detail = (await api.get(f"/changes/{change['id']}")).json()
            return detail["review_status"] == "completed" and len(detail["reviews"]) == 2

        await _until(reviewed)

        # 2) un push con commits hechos sin hooks también llega
        await asyncio.to_thread(
            os.rename, repo / ".git" / "hooks" / "post-commit", tmp_path / "off"
        )
        more = [await _commit(repo, f"f{i}.txt", f"feat: otro {i}") for i in range(2)]
        await asyncio.to_thread(
            os.rename, tmp_path / "off", repo / ".git" / "hooks" / "post-commit"
        )
        await asyncio.to_thread(_git, repo, "push", "-q", "origin", "main")

        async def pushed() -> bool:
            return {c["head_sha"] for c in await _channel(api, slug)} >= set(more)

        await _until(pushed)


async def test_removing_the_project_uninstalls_the_hooks_and_stops_the_flow(
    temporal_env: WorkflowEnvironment, database_url: str, tmp_path: Path
) -> None:
    repo, slug = _new_repo(tmp_path, "gadgets")
    user_hook = '#!/bin/sh\necho mio > "$(git rev-parse --show-toplevel)/hook-usuario.txt"\n'
    (repo / ".git" / "hooks" / "post-commit").write_text(user_hook)
    (repo / ".git" / "hooks" / "post-commit").chmod(0o755)
    target = temporal_env.client.service_client.config.target_host

    async with _workers(temporal_env, database_url), _server(database_url, target, tmp_path) as api:
        assert (
            await api.post("/projects", json={"path": str(repo)}, headers=HEADERS)
        ).status_code == 201
        await _commit(repo, "a.txt", "feat: con hooks")
        await _until(lambda: _has_changes(api, slug))
        assert (repo / "hook-usuario.txt").exists()  # su hook también corre

        removed = await api.delete(f"/projects/{slug}", headers=HEADERS)

        assert removed.status_code == 204
        assert (repo / ".git" / "hooks" / "post-commit").read_text() == user_hook  # restaurado
        assert not (repo / ".git" / "hooks" / "pre-push").exists()
        assert [p for p in (await api.get("/projects")).json() if p["slug"] == slug] == []
        assert (await api.get(f"/projects/{slug}/changes")).status_code == 404  # y sus changes


async def _has_changes(client: httpx.AsyncClient, slug: str) -> bool:
    return len(await _channel(client, slug)) > 0


async def test_sync_prs_registers_the_open_prs_through_gh_and_reviews_them(
    temporal_env: WorkflowEnvironment,
    database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, slug = _new_repo(tmp_path, "prs")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    listing = (
        '[{"number":7,"title":"feat: pr real","author":{"login":"ana"},"headRefName":"feature",'
        f'"headRefOid":"{"c" * 40}","url":"https://github.com/{slug}/pull/7",'
        '"updatedAt":"2026-10-10T10:00:00Z"}]'
    )
    gh = bin_dir / "gh"
    gh.write_text(
        "#!/bin/sh\n"
        f'if [ "$2" = "list" ]; then echo \'{listing}\'; else echo "diff --git a/x b/x"; fi\n'
    )
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    target = temporal_env.client.service_client.config.target_host

    async with _workers(temporal_env, database_url), _server(database_url, target, tmp_path) as api:
        await api.post("/projects", json={"path": str(repo)}, headers=HEADERS)

        first = await api.post(f"/projects/{slug}/sync-prs", headers=HEADERS)
        second = await api.post(f"/projects/{slug}/sync-prs", headers=HEADERS)

        assert (first.json(), second.json()) == (
            {"synced": 1, "created": 1},
            {"synced": 1, "created": 0},
        )
        (pr,) = await _channel(api, slug)
        assert (pr["kind"], pr["ref"], pr["title"], pr["author"]) == (
            "pr",
            "feature",
            "feat: pr real",
            "ana",
        )

        async def reviewed() -> bool:
            detail = (await api.get(f"/changes/{pr['id']}")).json()
            return detail["review_status"] == "completed"

        await _until(reviewed)


async def test_a_second_add_of_the_same_folder_is_409_and_the_hooks_stay_single(
    temporal_env: WorkflowEnvironment, database_url: str, tmp_path: Path
) -> None:
    repo, _slug = _new_repo(tmp_path, "dups")
    target = temporal_env.client.service_client.config.target_host

    async with _server(database_url, target, tmp_path) as api:
        first = await api.post("/projects", json={"path": str(repo)}, headers=HEADERS)
        again = await api.post("/projects", json={"path": str(repo)}, headers=HEADERS)
        hook = (repo / ".git" / "hooks" / "post-commit").read_text()

    assert (first.status_code, again.status_code) == (201, 409)
    assert hook.count("# >>> duelo >>>") == 1


async def test_with_the_feature_off_nothing_is_written_to_the_repo(
    temporal_env: WorkflowEnvironment,
    database_url: str,
    tmp_path: Path,
    session_factory: async_sessionmaker,
) -> None:
    repo, _slug = _new_repo(tmp_path, "off")
    settings = Settings(
        ingest_token=TOKEN,
        database_url=database_url,
        temporal_address=temporal_env.client.service_client.config.target_host,
    )
    deps = build_api_dependencies(settings)
    transport = httpx.ASGITransport(app=create_app(settings, deps))
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/projects", json={"path": str(repo)}, headers=HEADERS)
    finally:
        await deps.close()

    assert response.status_code == 404
    assert not (repo / ".git" / "hooks" / "post-commit").exists()
