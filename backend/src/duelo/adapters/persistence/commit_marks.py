from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from duelo.adapters.persistence.models import ChangeModel, EventModel
from duelo.adapters.persistence.sanitize import sanitize_json
from duelo.domain.change import ChangeKind
from duelo.domain.commit_state import TrackedCommit
from duelo.domain.events import CommitDiscarded, CommitRestored


class SqlAlchemyCommitMarks:
    """Adaptador del puerto `CommitMarks`: lo que el barrido de alcanzabilidad lee y marca.

    Cada llamada abre y cierra su propia sesión (como `SqlAlchemyProjectRepository`): el barrido
    corre en segundo plano y no debe dejar transacciones abiertas."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def tracked_commits(self, project_id: UUID) -> list[TrackedCommit]:
        async with self._session_factory() as session:
            rows = await session.execute(
                select(
                    ChangeModel.id,
                    ChangeModel.head_sha,
                    ChangeModel.created_at,
                    ChangeModel.discarded_at,
                ).where(
                    ChangeModel.project_id == project_id,
                    ChangeModel.kind == ChangeKind.COMMIT.value,
                )
            )
            return [
                TrackedCommit(
                    id=r.id,
                    head_sha=r.head_sha,
                    created_at=r.created_at,
                    discarded=r.discarded_at is not None,
                )
                for r in rows
            ]

    async def apply(
        self,
        project_id: UUID,
        *,
        discard: Sequence[UUID],
        restore: Sequence[UUID],
        at: datetime,
    ) -> tuple[int, int]:
        async with self._session_factory() as session, session.begin():
            # Solo cambian de estado (y emiten su evento) los changes que aún no lo tenían: dos
            # barridos simultáneos dejan una marca y un evento por change.
            discarded = await self._flip(
                session,
                project_id,
                discard,
                new_value=at,
                only_if_null=True,
                event=lambda change_id: CommitDiscarded(change_id=change_id, project_id=project_id),
            )
            restored = await self._flip(
                session,
                project_id,
                restore,
                new_value=None,
                only_if_null=False,
                event=lambda change_id: CommitRestored(change_id=change_id, project_id=project_id),
            )
        return len(discarded), len(restored)

    @staticmethod
    async def _flip(
        session: AsyncSession,
        project_id: UUID,
        change_ids: Sequence[UUID],
        *,
        new_value: datetime | None,
        only_if_null: bool,
        event: Callable[[UUID], CommitDiscarded | CommitRestored],
    ) -> list[UUID]:
        if not change_ids:
            return []
        current = ChangeModel.discarded_at
        stmt = (
            update(ChangeModel)
            .where(
                ChangeModel.id.in_(change_ids),
                ChangeModel.project_id == project_id,
                ChangeModel.kind == ChangeKind.COMMIT.value,
                current.is_(None) if only_if_null else current.is_not(None),
            )
            .values(discarded_at=new_value)
            .returning(ChangeModel.id)
        )
        changed = list((await session.execute(stmt)).scalars())
        for change_id in changed:
            built = event(change_id)
            await session.execute(
                insert(EventModel).values(
                    project_id=project_id,
                    type=built.type,
                    payload=sanitize_json(built.to_payload()),
                )
            )
        return changed
