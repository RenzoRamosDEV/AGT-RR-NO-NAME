from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, and_, func, insert, or_, select, true, tuple_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from duelo.adapters.persistence.models import ChangeModel, EventModel, ReviewModel
from duelo.adapters.persistence.sanitize import sanitize_json, sanitize_text
from duelo.application.read_models import ChangeCursor, ChangeSummary, ReviewBrief
from duelo.domain.change import Change, ChangeKind, ChangeStatus
from duelo.domain.diff import DiffSummary, FileDiff
from duelo.domain.events import ChangeCreated
from duelo.domain.review import ReviewStatus
from duelo.domain.review_status import ChangeReviewStatus, review_status_from_counts


class SqlAlchemyChangeRepository:
    """Adaptador del puerto `ChangeRepository` sobre SQLAlchemy async + Postgres."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, change: Change, event: ChangeCreated) -> Change:
        async with self._session.begin():
            insert_stmt = (
                pg_insert(ChangeModel)
                .values(
                    id=change.id,
                    project_id=change.project_id,
                    kind=change.kind.value,
                    ref=change.ref,
                    head_sha=change.head_sha,
                    title=sanitize_text(change.title),
                    author=sanitize_text(change.author),
                    url=change.url,
                    diff=sanitize_text(change.diff),
                    diff_truncated=change.diff_truncated,
                    status=change.status.value,
                    run=change.run,
                    created_at=change.created_at,
                    run_started_at=change.run_started_at,
                    diff_summary=_summary_to_json(change.diff_summary),
                )
                # La constraint UNIQUE (project_id, kind, head_sha) resuelve la
                # idempotencia de forma atómica: si ya existía, no se inserta fila y
                # RETURNING no devuelve nada - sin necesidad de capturar una excepción
                # específica del driver.
                .on_conflict_do_nothing(constraint="uq_changes_natural_key")
                .returning(ChangeModel.id)
            )
            inserted_id = (await self._session.execute(insert_stmt)).scalar_one_or_none()

            if inserted_id is None:
                existing_stmt = select(ChangeModel).where(
                    ChangeModel.project_id == change.project_id,
                    ChangeModel.kind == change.kind.value,
                    ChangeModel.head_sha == change.head_sha,
                )
                row = (await self._session.execute(existing_stmt)).scalar_one()
                return _to_domain(row)

            await self._session.execute(
                insert(EventModel).values(
                    project_id=event.project_id,
                    type=event.type,
                    payload=sanitize_json(event.to_payload()),
                )
            )
            return change

    async def get(self, change_id: UUID) -> Change | None:
        row = (
            await self._session.execute(select(ChangeModel).where(ChangeModel.id == change_id))
        ).scalar_one_or_none()
        return _to_domain(row) if row is not None else None

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        kind: ChangeKind | None,
        status: frozenset[ChangeReviewStatus] | None,
        q: str | None,
        expected_agents: int,
        limit: int,
        after: ChangeCursor | None,
    ) -> list[ChangeSummary]:
        # Contadores de reviews del `run` actual de CADA change, como LATERAL: Postgres recorre
        # los changes en el orden del índice y cuenta solo los de la página (index-only sobre
        # `reviews`) en vez de agregar todas las reviews del proyecto antes de ordenar.
        counts = (
            select(
                func.count()
                .filter(ReviewModel.status == ReviewStatus.COMPLETED.value)
                .label("completed"),
                func.count()
                .filter(ReviewModel.status == ReviewStatus.FAILED.value)
                .label("failed"),
            )
            .where(ReviewModel.change_id == ChangeModel.id, ReviewModel.run == ChangeModel.run)
            .correlate(ChangeModel)
            .lateral("review_counts")
        )
        completed = counts.c.completed
        failed = counts.c.failed

        # Se seleccionan columnas concretas (sin `diff`): un canal no debe mover diffs enteros.
        stmt = (
            select(
                ChangeModel.id,
                ChangeModel.project_id,
                ChangeModel.kind,
                ChangeModel.ref,
                ChangeModel.head_sha,
                ChangeModel.title,
                ChangeModel.author,
                ChangeModel.url,
                ChangeModel.diff_truncated,
                ChangeModel.status,
                ChangeModel.run,
                ChangeModel.created_at,
                ChangeModel.run_started_at,
                ChangeModel.diff_summary,
                completed.label("completed_reviews"),
                failed.label("failed_reviews"),
            )
            .join(counts, true())
            .where(ChangeModel.project_id == project_id)
            .order_by(ChangeModel.created_at.desc(), ChangeModel.id.desc())
            .limit(limit)
        )
        if kind is not None:
            stmt = stmt.where(ChangeModel.kind == kind.value)
        if status:
            stmt = stmt.where(
                or_(*(_status_predicate(s, completed, failed, expected_agents) for s in status))
            )
        if q:
            # `autoescape`: `%`, `_` y `\` de la búsqueda son texto, no comodines de LIKE.
            stmt = stmt.where(
                or_(
                    ChangeModel.title.icontains(q, autoescape=True),
                    ChangeModel.author.icontains(q, autoescape=True),
                    ChangeModel.head_sha.icontains(q, autoescape=True),
                    ChangeModel.ref.icontains(q, autoescape=True),
                )
            )
        if after is not None:
            stmt = stmt.where(
                tuple_(ChangeModel.created_at, ChangeModel.id) < tuple_(after.created_at, after.id)
            )
        rows = (await self._session.execute(stmt)).all()
        briefs = await self._briefs_for([r.id for r in rows])
        return [
            ChangeSummary(
                id=r.id,
                project_id=r.project_id,
                kind=ChangeKind(r.kind),
                ref=r.ref,
                head_sha=r.head_sha,
                title=r.title,
                author=r.author,
                url=r.url,
                diff_truncated=r.diff_truncated,
                status=ChangeStatus(r.status),
                review_status=review_status_from_counts(
                    completed=r.completed_reviews,
                    failed=r.failed_reviews,
                    expected_agents=expected_agents,
                ),
                run=r.run,
                created_at=r.created_at,
                run_started_at=r.run_started_at,
                diff_summary=_summary_from_json(r.diff_summary),
                reviews=briefs.get(r.id, ()),
            )
            for r in rows
        ]

    async def _briefs_for(self, change_ids: list[UUID]) -> dict[UUID, tuple[ReviewBrief, ...]]:
        """Reviews del `run` actual de los changes de la página, en UNA consulta (sin N+1) y solo
        con las columnas ligeras: ni `summary`, ni `findings`, ni `error`, ni `raw_output`."""
        if not change_ids:
            return {}
        rows = (
            await self._session.execute(
                select(
                    ReviewModel.change_id,
                    ReviewModel.agent,
                    ReviewModel.status,
                    ReviewModel.score,
                    ReviewModel.duration_ms,
                    ReviewModel.run,
                )
                .join(ChangeModel, ChangeModel.id == ReviewModel.change_id)
                .where(ChangeModel.id.in_(change_ids), ReviewModel.run == ChangeModel.run)
                .order_by(ReviewModel.change_id, ReviewModel.agent)
            )
        ).all()
        grouped: dict[UUID, list[ReviewBrief]] = {}
        for r in rows:
            grouped.setdefault(r.change_id, []).append(
                ReviewBrief(
                    agent=r.agent,
                    status=ReviewStatus(r.status),
                    score=r.score,
                    duration_ms=r.duration_ms,
                    run=r.run,
                )
            )
        return {change_id: tuple(items) for change_id, items in grouped.items()}

    async def advance_run(
        self, change_id: UUID, *, from_run: int, started_at: datetime
    ) -> Change | None:
        row = (
            await self._session.execute(
                update(ChangeModel)
                .where(ChangeModel.id == change_id, ChangeModel.run == from_run)
                .values(run=from_run + 1, run_started_at=started_at)
                .returning(ChangeModel)
            )
        ).scalar_one_or_none()
        # Compare-and-swap resuelto por la propia fila (READ COMMITTED reevalúa el WHERE al
        # desbloquearse). Se convierte antes del commit para no tocar atributos caducados.
        advanced = _to_domain(row) if row is not None else None
        await self._session.commit()
        return advanced


def _status_predicate(
    status: ChangeReviewStatus,
    completed: ColumnElement[int],
    failed: ColumnElement[int],
    expected_agents: int,
) -> ColumnElement[bool]:
    """Predicado SQL equivalente a `review_status_from_counts` (un test de integración recorre
    la matriz de contadores para garantizar que coinciden)."""
    total = completed + failed
    all_registered = and_(total > 0, total >= expected_agents)
    match status:
        case ChangeReviewStatus.PENDING:
            return total == 0
        case ChangeReviewStatus.RUNNING:
            return and_(total > 0, total < expected_agents)
        case ChangeReviewStatus.COMPLETED:
            return and_(all_registered, failed == 0)
        case ChangeReviewStatus.FAILED:
            return and_(all_registered, completed == 0)
        case ChangeReviewStatus.PARTIAL_FAILED:
            return and_(all_registered, completed > 0, failed > 0)


def _to_domain(row: ChangeModel) -> Change:
    return Change(
        id=row.id,
        project_id=row.project_id,
        kind=ChangeKind(row.kind),
        ref=row.ref,
        head_sha=row.head_sha,
        title=row.title,
        author=row.author,
        url=row.url,
        diff=row.diff,
        diff_truncated=row.diff_truncated,
        status=ChangeStatus(row.status),
        run=row.run,
        created_at=row.created_at,
        run_started_at=row.run_started_at,
        diff_summary=_summary_from_json(row.diff_summary),
    )


def _summary_to_json(summary: DiffSummary) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "files_changed": summary.files_changed,
        "additions": summary.additions,
        "deletions": summary.deletions,
        "files": [
            {"path": f.path, "additions": f.additions, "deletions": f.deletions}
            for f in summary.files
        ],
    }
    sanitized: dict[str, Any] = sanitize_json(payload)
    return sanitized


def _summary_from_json(data: dict[str, Any]) -> DiffSummary:
    return DiffSummary(
        files_changed=int(data["files_changed"]),
        additions=int(data["additions"]),
        deletions=int(data["deletions"]),
        files=tuple(
            FileDiff(
                path=str(f["path"]), additions=int(f["additions"]), deletions=int(f["deletions"])
            )
            for f in data["files"]
        ),
    )
