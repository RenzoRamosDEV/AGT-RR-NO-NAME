from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field

from duelo.application.ingest_commit import CommitSubmission
from duelo.domain.change import Change

Check = Callable[[], Awaitable[None]]


async def _noop() -> None:
    return None


@dataclass
class ApiDependencies:
    """Lo que la API necesita del exterior. La composición real (Postgres, Temporal) vive en
    `duelo.composition`; los tests pasan fakes. Así `entrypoints/` no importa adapters."""

    ingest_commit: Callable[[CommitSubmission], Awaitable[Change]]
    readiness_checks: Mapping[str, Check] = field(default_factory=dict)
    close: Callable[[], Awaitable[None]] = _noop
