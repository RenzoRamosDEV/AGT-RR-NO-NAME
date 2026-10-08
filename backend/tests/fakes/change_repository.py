from __future__ import annotations

from uuid import UUID

from review_arena.domain.change import Change
from review_arena.domain.events import ChangeCreated


class FakeChangeRepository:
    """Repositorio en memoria para testear `ingest_change` sin Postgres."""

    def __init__(self) -> None:
        self._by_natural_key: dict[tuple[str, str, str], Change] = {}
        self._by_id: dict[UUID, Change] = {}
        self.persisted_events: list[ChangeCreated] = []

    async def add(self, change: Change, event: ChangeCreated) -> Change:
        key = (str(change.project_id), change.kind.value, change.head_sha)
        existing = self._by_natural_key.get(key)
        if existing is not None:
            return existing

        self._by_natural_key[key] = change
        self._by_id[change.id] = change
        self.persisted_events.append(event)
        return change

    async def get(self, change_id: UUID) -> Change | None:
        return self._by_id.get(change_id)
