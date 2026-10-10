"""El sincronizador periódico y el ciclo de vida de los trabajos en segundo plano."""

from __future__ import annotations

import asyncio
import logging

import pytest

from duelo.config import Settings
from duelo.entrypoints.api import background
from duelo.entrypoints.api.app import create_app
from duelo.entrypoints.api.background import periodic
from duelo.entrypoints.api.dependencies import ApiDependencies
from tests.fakes.api import build_fake_api


class StopLoop(Exception):
    """Corta el bucle infinito en los tests (hace de cancelación)."""


async def test_runs_the_job_now_and_after_every_interval() -> None:
    sleeps: list[float] = []
    runs = 0

    async def job() -> None:
        nonlocal runs
        runs += 1

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 3:
            raise StopLoop

    with pytest.raises(StopLoop):
        await periodic(300, job, sleep=sleep)

    assert runs == 3 and sleeps == [300, 300, 300]  # ejecuta primero y duerme después


async def test_a_failing_job_is_logged_and_the_loop_goes_on(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `alembic` (fileConfig) deshabilita los loggers ya creados si un test de migraciones corrió
    # antes en el mismo proceso: aquí se vuelve a habilitar el que se comprueba.
    monkeypatch.setattr(background.logger, "disabled", False)
    runs = 0

    async def job() -> None:
        nonlocal runs
        runs += 1
        if runs == 1:
            raise RuntimeError("falló gh")

    async def sleep(_: float) -> None:
        if runs == 2:
            raise StopLoop

    with caplog.at_level(logging.WARNING), pytest.raises(StopLoop):
        await periodic(1, job, sleep=sleep)

    assert runs == 2
    assert "Falló un trabajo periódico" in caplog.text and "falló gh" in caplog.text


async def test_cancelling_the_periodic_task_stops_it() -> None:
    started = asyncio.Event()

    async def job() -> None:
        started.set()

    task = asyncio.create_task(periodic(3600, job))
    await asyncio.wait_for(started.wait(), 2)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


async def test_the_app_starts_its_background_jobs_and_cancels_them_on_shutdown() -> None:
    events: list[str] = []
    running = asyncio.Event()

    async def job() -> None:
        events.append("start")
        running.set()
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            events.append("cancelled")
            raise

    base = build_fake_api().app.state.dependencies
    deps = ApiDependencies(**{**vars(base), "background_jobs": [job]})
    app = create_app(Settings(ingest_token="t"), deps)  # type: ignore[call-arg]

    async with app.router.lifespan_context(app):
        await asyncio.wait_for(running.wait(), 2)
        assert events == ["start"]

    assert events == ["start", "cancelled"]


async def test_the_app_without_background_jobs_starts_and_closes_cleanly() -> None:
    closed: list[bool] = []

    async def close() -> None:
        closed.append(True)

    base = build_fake_api().app.state.dependencies
    deps = ApiDependencies(**{**vars(base), "close": close})
    app = create_app(Settings(ingest_token="t"), deps)  # type: ignore[call-arg]

    async with app.router.lifespan_context(app):
        pass

    assert closed == [True]
