"""Doble de test de `ProjectSlugs`."""

from __future__ import annotations

from uuid import UUID


class FakeProjectSlugs:
    """Nombre de proyecto por id; `default` es lo que devuelve para un id que no conoce."""

    def __init__(self, slugs: dict[UUID, str] | None = None, *, default: str | None = None) -> None:
        self._slugs = slugs or {}
        self._default = default

    async def slug_of(self, project_id: UUID) -> str | None:
        return self._slugs.get(project_id, self._default)
