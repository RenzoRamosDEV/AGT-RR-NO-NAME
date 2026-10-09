from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from duelo.adapters.persistence.models import ProjectModel
from duelo.domain.project import Project


class SqlAlchemyProjectRepository:
    """Lectura corta con su propia sesión: así la consulta no deja una transacción abierta
    que choque con el `session.begin()` que usa `SqlAlchemyChangeRepository.add`."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_by_slug(self, slug: str) -> Project | None:
        if "\x00" in slug:  # ningún proyecto puede llamarse así y Postgres rechazaría la consulta
            return None
        async with self._session_factory() as session:
            row = (
                await session.execute(select(ProjectModel).where(ProjectModel.slug == slug))
            ).scalar_one_or_none()
        return Project(id=row.id, slug=row.slug) if row is not None else None
