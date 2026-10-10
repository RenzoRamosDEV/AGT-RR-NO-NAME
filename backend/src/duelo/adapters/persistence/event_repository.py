from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from duelo.adapters.persistence.models import EventModel
from duelo.application.read_models import StoredEvent


class SqlAlchemyChangeEventRepository:
    """Adaptador del puerto `ChangeEventRepository`: lee el outbox (`events`)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_change(self, project_id: UUID, change_id: UUID) -> list[StoredEvent]:
        rows = await self._session.execute(
            select(EventModel)
            .where(
                EventModel.project_id == project_id,
                # Coincide con el índice de expresión `ix_events_change_id`.
                EventModel.payload["change_id"].astext == str(change_id),
            )
            # El instante manda; el id desempata. Ordenar solo por id cruzaría eventos escritos
            # casi a la vez por reviews concurrentes.
            .order_by(EventModel.created_at, EventModel.id)
        )
        return [
            StoredEvent(id=r.id, type=r.type, payload=r.payload, created_at=r.created_at)
            for r in rows.scalars()
        ]
