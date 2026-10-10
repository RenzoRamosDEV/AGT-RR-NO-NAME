"""Apagado ordenado y telemetría del worker, sin Temporal: las señales piden parar, los workers
se paran a la vez (ninguno sigue aceptando tareas mientras otro agota su plazo de gracia), un
worker caído arrastra a los demás, y sin dirección de métricas no se crea ningún `Runtime`."""

from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import AsyncIterator

import pytest

from duelo.config import WorkerSettings
from duelo.worker import build_runtime, install_stop_signals, run_until_stopped


class RecordingWorker:
    """Imita `Worker.run()` / `shutdown()`: corre hasta que le piden parar y anota cada paso.
    `shutdown()` tarda `grace` segundos, como el plazo de gracia real."""

    def __init__(self, name: str, log: list[str], *, grace: float = 0.0) -> None:
        self.name = name
        self._log = log
        self._grace = grace
        self._stopped = asyncio.Event()

    async def run(self) -> None:
        self._log.append(f"{self.name}:up")
        await self._stopped.wait()
        self._log.append(f"{self.name}:down")

    async def shutdown(self) -> None:
        self._log.append(f"{self.name}:stopping")
        await asyncio.sleep(self._grace)
        self._stopped.set()


class CrashingWorker(RecordingWorker):
    async def run(self) -> None:
        self._log.append(f"{self.name}:up")
        raise ConnectionError("Temporal se fue")


@pytest.fixture
async def stop_signals() -> AsyncIterator[asyncio.Event]:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    install_stop_signals(loop, stop)
    yield stop
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.remove_signal_handler(sig)


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGINT])
async def test_a_stop_signal_stops_every_worker_at_once(
    stop_signals: asyncio.Event, sig: signal.Signals
) -> None:
    log: list[str] = []
    workers = [RecordingWorker("platform", log), RecordingWorker("agents", log, grace=0.05)]
    running = asyncio.create_task(run_until_stopped(workers, stop_signals))
    await asyncio.sleep(0.02)  # `run_until_stopped` crea a su vez una tarea por worker
    assert log == ["platform:up", "agents:up"]

    os.kill(os.getpid(), sig)
    await asyncio.wait_for(running, timeout=5)

    # Los dos reciben la orden de parar antes de que ninguno termine: `platform` no sigue
    # aceptando workflow tasks mientras `agents` agota su plazo de gracia.
    assert log[2:4] == ["platform:stopping", "agents:stopping"]
    assert sorted(log[4:]) == ["agents:down", "platform:down"]


async def test_without_a_signal_the_workers_stay_up() -> None:
    log: list[str] = []
    stop = asyncio.Event()
    running = asyncio.create_task(run_until_stopped([RecordingWorker("platform", log)], stop))
    await asyncio.sleep(0.05)

    assert not running.done()
    assert log == ["platform:up"]

    stop.set()
    await asyncio.wait_for(running, timeout=5)
    assert log == ["platform:up", "platform:stopping", "platform:down"]


async def test_a_worker_that_crashes_stops_the_others_and_surfaces_its_error() -> None:
    log: list[str] = []
    stop = asyncio.Event()
    workers = [RecordingWorker("platform", log), CrashingWorker("agents", log)]

    with pytest.raises(ConnectionError, match="Temporal se fue"):
        await asyncio.wait_for(run_until_stopped(workers, stop), timeout=5)

    assert "platform:stopping" in log
    assert "platform:down" in log


def test_without_a_metrics_address_there_is_no_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEMPORAL_METRICS_ADDRESS", raising=False)
    assert build_runtime(WorkerSettings()) is None

    monkeypatch.setenv("TEMPORAL_METRICS_ADDRESS", "")
    assert build_runtime(WorkerSettings()) is None
