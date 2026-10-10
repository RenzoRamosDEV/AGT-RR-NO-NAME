from __future__ import annotations

from duelo.application.ports import ProjectAlreadyExists
from duelo.domain.project import Project


class FakeProjectRepository:
    """Repositorio de proyectos en memoria; también hace de catálogo de proyectos locales."""

    def __init__(self, *projects: Project) -> None:
        self._by_slug = {p.slug: p for p in projects}

    async def get_by_slug(self, slug: str) -> Project | None:
        return self._by_slug.get(slug)

    async def list_all(self) -> list[Project]:
        return sorted(self._by_slug.values(), key=lambda p: p.slug)

    async def add_local(self, project: Project) -> Project:
        taken_paths = {p.path for p in self._by_slug.values() if p.path is not None}
        if project.slug in self._by_slug or project.path in taken_paths:
            raise ProjectAlreadyExists(project.slug)
        self._by_slug[project.slug] = project
        return project

    async def remove(self, slug: str) -> Project | None:
        return self._by_slug.pop(slug, None)

    async def list_local(self) -> list[Project]:
        return [p for p in await self.list_all() if p.path is not None]
