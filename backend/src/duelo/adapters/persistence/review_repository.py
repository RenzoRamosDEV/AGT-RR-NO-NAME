from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from duelo.adapters.persistence.models import ChangeModel, EventModel, ReviewModel
from duelo.adapters.persistence.sanitize import sanitize_json, sanitize_text
from duelo.application.read_models import AgentStats
from duelo.domain.events import ReviewCompleted, ReviewFailed, ReviewReused
from duelo.domain.review import Finding, Review, ReviewStatus

ReviewEvent = ReviewCompleted | ReviewFailed | ReviewReused


async def insert_review(session: AsyncSession, review: Review, event: ReviewEvent) -> Review:
    """Inserta la review y su evento en la transacción en curso, de forma idempotente.

    La constraint UNIQUE (change_id, agent, run) resuelve la idempotencia de forma atómica: si ya
    existía, devuelve la fila existente sin crear un segundo evento. Lo comparten este repositorio y
    el de changes (que copia las reviews de un commit en el alta de su PR)."""
    insert_stmt = (
        pg_insert(ReviewModel)
        .values(
            id=review.id,
            change_id=review.change_id,
            agent=review.agent,
            run=review.run,
            status=review.status.value,
            summary=sanitize_text(review.summary),
            score=review.score,
            findings=sanitize_json(
                [
                    {
                        "severity": f.severity,
                        "file": f.file,
                        "line": f.line,
                        "message": f.message,
                    }
                    for f in review.findings
                ]
            ),
            raw_output=sanitize_text(review.raw_output),
            duration_ms=review.duration_ms,
            error=sanitize_text(review.error),
            created_at=review.created_at,
            reused_from_change_id=review.reused_from_change_id,
        )
        .on_conflict_do_nothing(constraint="uq_reviews_natural_key")
        .returning(ReviewModel.id)
    )
    inserted_id = (await session.execute(insert_stmt)).scalar_one_or_none()

    if inserted_id is None:
        existing_stmt = select(ReviewModel).where(
            ReviewModel.change_id == review.change_id,
            ReviewModel.agent == review.agent,
            ReviewModel.run == review.run,
        )
        row = (await session.execute(existing_stmt)).scalar_one()
        return review_from_row(row)

    await session.execute(
        insert(EventModel).values(
            project_id=event.project_id,
            type=event.type,
            payload=sanitize_json(event.to_payload()),
        )
    )
    return review


class SqlAlchemyReviewRepository:
    """Adaptador del puerto `ReviewRepository` sobre SQLAlchemy async + Postgres."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, review: Review, event: ReviewEvent) -> Review:
        async with self._session.begin():
            return await insert_review(self._session, review, event)

    async def list_for_change(self, change_id: UUID) -> list[Review]:
        rows = await self._session.execute(
            select(ReviewModel)
            .where(ReviewModel.change_id == change_id)
            .order_by(ReviewModel.created_at, ReviewModel.agent, ReviewModel.run)
        )
        return [review_from_row(row) for row in rows.scalars()]

    async def get(self, review_id: UUID) -> Review | None:
        row = (
            await self._session.execute(select(ReviewModel).where(ReviewModel.id == review_id))
        ).scalar_one_or_none()
        return review_from_row(row) if row is not None else None

    async def agent_stats(self, *, project_id: UUID | None) -> list[AgentStats]:
        completed = ReviewStatus.COMPLETED.value
        failed = ReviewStatus.FAILED.value
        stmt = (
            select(
                ReviewModel.agent,
                func.count().label("total"),
                func.count().filter(ReviewModel.status == completed).label("completed"),
                func.count().filter(ReviewModel.status == failed).label("failed"),
                func.avg(ReviewModel.duration_ms).label("avg_duration_ms"),
                func.avg(ReviewModel.score).label("avg_score"),
            )
            .group_by(ReviewModel.agent)
            .order_by(ReviewModel.agent)
        )
        if project_id is not None:
            stmt = stmt.join(ChangeModel, ChangeModel.id == ReviewModel.change_id).where(
                ChangeModel.project_id == project_id
            )
        rows = await self._session.execute(stmt)
        return [
            AgentStats(
                agent=r.agent,
                total=r.total,
                completed=r.completed,
                failed=r.failed,
                avg_duration_ms=None if r.avg_duration_ms is None else float(r.avg_duration_ms),
                avg_score=None if r.avg_score is None else float(r.avg_score),
            )
            for r in rows
        ]


def review_from_row(row: ReviewModel) -> Review:
    return Review(
        id=row.id,
        change_id=row.change_id,
        agent=row.agent,
        run=row.run,
        status=ReviewStatus(row.status),
        summary=row.summary,
        score=row.score,
        findings=tuple(
            Finding(
                severity=str(f["severity"]),
                file=str(f["file"]),
                line=int(f["line"]),  # type: ignore[call-overload]
                message=str(f["message"]),
            )
            for f in row.findings
        ),
        raw_output=row.raw_output,
        duration_ms=row.duration_ms,
        error=row.error,
        created_at=row.created_at,
        reused_from_change_id=row.reused_from_change_id,
    )
