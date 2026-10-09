from __future__ import annotations

from uuid import UUID

from duelo.application.read_models import ChangeCursor, ChangeSummary
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated


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

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        kind: ChangeKind | None,
        limit: int,
        after: ChangeCursor | None,
    ) -> list[ChangeSummary]:
        rows = [
            c
            for c in self._by_id.values()
            if c.project_id == project_id and (kind is None or c.kind == kind)
        ]
        rows.sort(key=lambda c: (c.created_at, c.id), reverse=True)
        if after is not None:
            rows = [c for c in rows if (c.created_at, c.id) < (after.created_at, after.id)]
        return [
            ChangeSummary(
                id=c.id,
                project_id=c.project_id,
                kind=c.kind,
                ref=c.ref,
                head_sha=c.head_sha,
                title=c.title,
                author=c.author,
                url=c.url,
                diff_truncated=c.diff_truncated,
                status=c.status,
                run=c.run,
                created_at=c.created_at,
            )
            for c in rows[:limit]
        ]
