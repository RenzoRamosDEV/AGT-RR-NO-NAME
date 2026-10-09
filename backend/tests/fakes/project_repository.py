from __future__ import annotations

from review_arena.domain.project import Project


class FakeProjectRepository:
    def __init__(self, *projects: Project) -> None:
        self._by_slug = {p.slug: p for p in projects}

    async def get_by_slug(self, slug: str) -> Project | None:
        return self._by_slug.get(slug)
