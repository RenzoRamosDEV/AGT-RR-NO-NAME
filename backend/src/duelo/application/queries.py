"""Casos de uso de solo lectura que alimentan la API de consulta."""

from __future__ import annotations

from uuid import UUID

from duelo.application.ingest_commit import ProjectNotFound
from duelo.application.ports import (
    ChangeEventRepository,
    ChangeRepository,
    ProjectRepository,
    ReviewRepository,
)
from duelo.application.read_models import (
    AgentStats,
    ChangeCursor,
    ChangeDetail,
    ChangeEvent,
    ChangePage,
    RawOutput,
    StoredEvent,
)
from duelo.domain.change import ChangeKind
from duelo.domain.project import Project
from duelo.domain.review import ReviewStatus
from duelo.domain.review_status import (
    ChangeReviewStatus,
    review_status_of_run,
    summarize_severities,
)


async def list_projects(projects: ProjectRepository) -> list[Project]:
    return await projects.list_all()


async def list_changes(
    projects: ProjectRepository,
    changes: ChangeRepository,
    *,
    slug: str,
    kind: ChangeKind | None,
    status: frozenset[ChangeReviewStatus] | None,
    q: str | None,
    expected_agents: int,
    limit: int,
    after: ChangeCursor | None,
) -> ChangePage:
    project = await projects.get_by_slug(slug)
    if project is None:
        raise ProjectNotFound(slug)

    # Se pide uno de más para saber si quedan elementos sin una segunda consulta.
    rows = await changes.list_for_project(
        project.id,
        kind=kind,
        status=status,
        q=q,
        expected_agents=expected_agents,
        limit=limit + 1,
        after=after,
    )
    page = rows[:limit]
    last = page[-1] if len(rows) > limit else None
    next_cursor = ChangeCursor(created_at=last.created_at, id=last.id) if last else None
    return ChangePage(items=tuple(page), next_cursor=next_cursor)


async def get_change_detail(
    changes: ChangeRepository,
    reviews: ReviewRepository,
    change_id: UUID,
    *,
    expected_agents: int,
) -> ChangeDetail | None:
    change = await changes.get(change_id)
    if change is None:
        return None
    rows = await reviews.list_for_change(change_id)
    # Los findings de runs anteriores quedaron superados por el reintento: no cuentan.
    findings = summarize_severities(
        f.severity
        for r in rows
        if r.run == change.run and r.status is ReviewStatus.COMPLETED
        for f in r.findings
    )
    return ChangeDetail(
        change=change,
        reviews=tuple(rows),
        review_status=review_status_of_run(change.run, rows, expected_agents=expected_agents),
        findings_summary=findings,
    )


async def agent_stats(
    projects: ProjectRepository, reviews: ReviewRepository, *, project: str | None
) -> list[AgentStats]:
    """Métricas por agente, globales o de un proyecto (`ProjectNotFound` si no existe)."""
    if project is None:
        return await reviews.agent_stats(project_id=None)
    found = await projects.get_by_slug(project)
    if found is None:
        raise ProjectNotFound(project)
    return await reviews.agent_stats(project_id=found.id)


# Lista blanca de lo que la API muestra de un evento: lo que no esté aquí (el `error` de una
# review fallida, campos futuros del payload) no sale nunca, aunque esté guardado.
_EXPOSED_EVENT_TYPES = frozenset({"change.created", "review.completed", "review.failed"})


def _as_uuid(value: object) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _expose(event: StoredEvent) -> ChangeEvent | None:
    if event.type not in _EXPOSED_EVENT_TYPES:
        return None
    agent = event.payload.get("agent")
    return ChangeEvent(
        id=event.id,
        type=event.type,
        created_at=event.created_at,
        agent=agent if isinstance(agent, str) else None,
        review_id=_as_uuid(event.payload["review_id"]) if "review_id" in event.payload else None,
    )


async def change_events(
    changes: ChangeRepository, events: ChangeEventRepository, change_id: UUID
) -> list[ChangeEvent] | None:
    """Línea de tiempo del change con el payload reducido, o `None` si el change no existe."""
    change = await changes.get(change_id)
    if change is None:
        return None
    stored = await events.list_for_change(change.project_id, change_id)
    return [e for e in (_expose(s) for s in stored) if e is not None]


async def review_raw_output(reviews: ReviewRepository, review_id: UUID) -> RawOutput | None:
    """Salida cruda de una review; `None` si no existe o no tiene (las fallidas no la tienen)."""
    review = await reviews.get(review_id)
    if review is None or review.raw_output is None:
        return None
    return RawOutput(review_id=review.id, raw_output=review.raw_output)
