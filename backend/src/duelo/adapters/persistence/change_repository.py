from __future__ import annotations

from uuid import UUID

from sqlalchemy import insert, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from duelo.adapters.persistence.models import ChangeModel, EventModel
from duelo.adapters.persistence.sanitize import sanitize_json, sanitize_text
from duelo.application.read_models import ChangeCursor, ChangeSummary
from duelo.domain.change import Change, ChangeKind, ChangeStatus
from duelo.domain.events import ChangeCreated


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
        limit: int,
        after: ChangeCursor | None,
    ) -> list[ChangeSummary]:
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
            )
            .where(ChangeModel.project_id == project_id)
            .order_by(ChangeModel.created_at.desc(), ChangeModel.id.desc())
            .limit(limit)
        )
        if kind is not None:
            stmt = stmt.where(ChangeModel.kind == kind.value)
        if after is not None:
            stmt = stmt.where(
                tuple_(ChangeModel.created_at, ChangeModel.id) < tuple_(after.created_at, after.id)
            )
        rows = (await self._session.execute(stmt)).all()
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
                run=r.run,
                created_at=r.created_at,
            )
            for r in rows
        ]


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
    )
