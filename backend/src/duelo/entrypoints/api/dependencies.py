from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from duelo.application.ingest_commit import ChangeSubmission, IngestResult
from duelo.application.local_projects import SyncResult
from duelo.application.ports import RateLimiter
from duelo.application.read_models import (
    AgentStats,
    ChangeCursor,
    ChangeDetail,
    ChangeEvent,
    ChangePage,
    RawOutput,
)
from duelo.domain.change import Change, ChangeKind
from duelo.domain.project import Project
from duelo.domain.review_status import ChangeReviewStatus

Check = Callable[[], Awaitable[None]]


async def _noop() -> None:
    return None


@dataclass
class ApiDependencies:
    """Lo que la API necesita del exterior. La composición real (Postgres, Temporal) vive en
    `duelo.composition`; los tests pasan fakes. Así `entrypoints/` no importa adapters."""

    ingest_commit: Callable[[ChangeSubmission], Awaitable[IngestResult]]
    ingest_pr: Callable[[ChangeSubmission], Awaitable[IngestResult]]
    list_projects: Callable[[], Awaitable[list[Project]]]
    # Lanza `ProjectNotFound` si el slug no existe.
    list_changes: Callable[
        [
            str,
            ChangeKind | None,
            frozenset[ChangeReviewStatus] | None,
            str | None,
            int,
            ChangeCursor | None,
        ],
        Awaitable[ChangePage],
    ]
    get_change: Callable[[UUID], Awaitable[ChangeDetail | None]]
    # Lanza `ChangeNotFound`, `RetryNotAllowed` o `ReviewStartError`; devuelve el change con su run.
    retry_review: Callable[[UUID], Awaitable[Change]]
    # `None` = estadísticas globales; lanza `ProjectNotFound` si el slug no existe.
    agent_stats: Callable[[str | None], Awaitable[list[AgentStats]]]
    # `None` si el change no existe.
    list_change_events: Callable[[UUID], Awaitable[list[ChangeEvent] | None]]
    # `None` si la review no existe o no tiene salida cruda.
    get_review_raw_output: Callable[[UUID], Awaitable[RawOutput | None]]
    # Proyectos desde carpetas locales (LOCAL_PROJECTS_ENABLED): `None` = función no cableada y
    # sus endpoints responden 404. Lanzan `InvalidRepository`, `ProjectAlreadyExists`,
    # `HookInstallError`, `ProjectNotFound`, `ProjectHasNoFolder`, `GithubUnavailable`...
    add_local_project: Callable[[str], Awaitable[Project]] | None = None
    remove_project: Callable[[str], Awaitable[None]] | None = None
    sync_pull_requests: Callable[[str], Awaitable[SyncResult]] | None = None
    # Trabajos de larga duración que la app arranca al iniciar y cancela al cerrar.
    background_jobs: Sequence[Callable[[], Coroutine[Any, Any, None]]] = ()
    readiness_checks: Mapping[str, Check] = field(default_factory=dict)
    # `None` = sin límite de peticiones (RATE_LIMIT_REQUESTS=0).
    rate_limiter: RateLimiter | None = None
    close: Callable[[], Awaitable[None]] = _noop
