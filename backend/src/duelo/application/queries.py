"""Casos de uso de solo lectura que alimentan la API de consulta."""

from __future__ import annotations

from uuid import UUID

from duelo.application.ingest_commit import ProjectNotFound
from duelo.application.ports import ChangeRepository, ProjectRepository, ReviewRepository
from duelo.application.read_models import (
    AgentStats,
    ChangeCursor,
    ChangeDetail,
    ChangePage,
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


async def agent_stats(reviews: ReviewRepository) -> list[AgentStats]:
    return await reviews.agent_stats()
