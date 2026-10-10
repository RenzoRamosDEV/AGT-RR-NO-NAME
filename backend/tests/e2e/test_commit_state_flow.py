"""Commits deshechos y revertidos de punta a punta: API real por HTTP (uvicorn) + Postgres real +
Temporal de test + workers, un repositorio git real con los hooks reales que instala la API y el
barrido de alcanzabilidad corriendo cada segundo.

El criterio de «hecho»: hago `git reset`, `git revert` y `git commit --amend` en mi repositorio y el
canal de Duelo lo refleja sin que yo llame a ninguna API.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from temporalio.testing import WorkflowEnvironment

from tests.e2e.test_ingest_flow import HEADERS, _until, _workers
from tests.e2e.test_local_projects_flow import (  # noqa: F401 - `_git_env` es un fixture autouse
    _channel,
    _commit,
    _git,
    _git_env,
    _new_repo,
    _server,
)


async def _by_sha(api: httpx.AsyncClient, slug: str) -> dict[str, dict]:
    return {c["head_sha"]: c for c in await _channel(api, slug)}


def _is(api: httpx.AsyncClient, slug: str, sha: str, state: str):
    async def check() -> bool:
        change = (await _by_sha(api, slug)).get(sha)
        return change is not None and change["commit_state"] == state

    return check


async def _event_types(api: httpx.AsyncClient, change_id: str) -> list[str]:
    return [e["type"] for e in (await api.get(f"/changes/{change_id}/events")).json()]


async def test_reset_revert_and_amend_show_up_in_the_channel_without_calling_any_api(
    temporal_env: WorkflowEnvironment, database_url: str, tmp_path: Path
) -> None:
    repo, slug = _new_repo(tmp_path, "widgets")
    target = temporal_env.client.service_client.config.target_host

    async with (
        _workers(temporal_env, database_url),
        _server(database_url, target, tmp_path, reachability_sweep_interval_seconds=1) as api,
    ):
        added = await api.post("/projects", json={"path": str(repo)}, headers=HEADERS)
        assert added.status_code == 201, added.text

        sha_a = await _commit(repo, "a.py", "feat: uno")
        sha_b = await _commit(repo, "b.py", "feat: dos")

        async def both_arrived() -> bool:
            return {sha_a, sha_b} <= set(await _by_sha(api, slug))

        await _until(both_arrived)
        channel = await _by_sha(api, slug)
        assert channel[sha_a]["commit_state"] == channel[sha_b]["commit_state"] == "active"
        assert channel[sha_a]["reverted_by"] is None

        # 1) `git reset --hard HEAD~1`: el segundo commit deja de estar en la rama.
        await asyncio.to_thread(_git, repo, "reset", "--hard", "-q", "HEAD~1")
        await _until(_is(api, slug, sha_b, "discarded"))
        channel = await _by_sha(api, slug)
        assert channel[sha_a]["commit_state"] == "active"
        # El change y sus reviews se conservan: solo se marca.
        assert channel[sha_b]["review_status"] == channel[sha_a]["review_status"] == "completed"
        assert await _event_types(api, channel[sha_b]["id"]) == [
            "change.created",
            "review.completed",
            "review.completed",
            "commit.discarded",
        ]

        # 2) Se recupera (`git reset --hard <sha>`): vuelve a estar activo.
        await asyncio.to_thread(_git, repo, "reset", "--hard", "-q", sha_b)
        await _until(_is(api, slug, sha_b, "active"))
        events = await _event_types(api, (await _by_sha(api, slug))[sha_b]["id"])
        assert events[-2:] == ["commit.discarded", "commit.restored"]

        # 3) `git revert`: el hook envía el cuerpo («This reverts commit …») y el original queda
        #    revertido por el nuevo commit, que sigue activo.
        await asyncio.to_thread(_git, repo, "revert", "--no-edit", sha_b)
        revert_one = (await asyncio.to_thread(_git, repo, "rev-parse", "HEAD")).strip()

        async def reverted_by_it() -> bool:
            channel = await _by_sha(api, slug)
            original = channel.get(sha_b)
            return (
                original is not None
                and original["commit_state"] == "reverted"
                and original["reverted_by"]
                == {"id": channel[revert_one]["id"], "head_sha": revert_one}
            )

        await _until(reverted_by_it)
        channel = await _by_sha(api, slug)
        assert channel[revert_one]["commit_state"] == "active"
        assert channel[sha_a]["commit_state"] == "active"
        assert "commit.reverted" in await _event_types(api, channel[sha_b]["id"])
        detail = (await api.get(f"/changes/{channel[sha_b]['id']}")).json()
        assert (detail["commit_state"], detail["reverted_by"]["head_sha"]) == (
            "reverted",
            revert_one,
        )

        # 4) Se deshace el propio revert: el original ya no está revertido.
        await asyncio.to_thread(_git, repo, "reset", "--hard", "-q", "HEAD~1")
        await _until(_is(api, slug, revert_one, "discarded"))
        await _until(_is(api, slug, sha_b, "active"))
        assert (await _by_sha(api, slug))[sha_b]["reverted_by"] is None

        # 5) Se revierte otra vez y se corrige el revert con `--amend`: el SHA cambia, el barrido
        #    marca el antiguo y el original queda revertido por el nuevo.
        await asyncio.sleep(1.1)  # fechas distintas: otro SHA
        await asyncio.to_thread(_git, repo, "revert", "--no-edit", sha_b)
        revert_two = (await asyncio.to_thread(_git, repo, "rev-parse", "HEAD")).strip()
        await _until(_is(api, slug, sha_b, "reverted"))
        await asyncio.sleep(1.1)
        await asyncio.to_thread(_git, repo, "commit", "-q", "--amend", "--no-edit")
        amended = (await asyncio.to_thread(_git, repo, "rev-parse", "HEAD")).strip()
        assert amended != revert_two

        async def replaced() -> bool:
            channel = await _by_sha(api, slug)
            if amended not in channel or revert_two not in channel:
                return False
            original = channel[sha_b]
            return (
                channel[revert_two]["commit_state"] == "discarded"
                and original["commit_state"] == "reverted"
                and original["reverted_by"]["head_sha"] == amended
            )

        await _until(replaced)
