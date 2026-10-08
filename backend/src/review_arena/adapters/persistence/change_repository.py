from __future__ import annotations

from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from review_arena.adapters.persistence.models import ChangeModel, EventModel
from review_arena.domain.change import Change, ChangeKind
from review_arena.domain.events import ChangeCreated


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
                    title=change.title,
                    author=change.author,
                    url=change.url,
                    diff=change.diff,
                    diff_truncated=change.diff_truncated,
                    status=change.status,
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
                    payload=event.to_payload(),
                )
            )
            return change


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
        status=row.status,
        run=row.run,
        created_at=row.created_at,
    )
