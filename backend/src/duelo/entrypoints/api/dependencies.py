from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from uuid import UUID

from duelo.application.ingest_commit import ChangeSubmission, IngestResult
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
    readiness_checks: Mapping[str, Check] = field(default_factory=dict)
    close: Callable[[], Awaitable[None]] = _noop
