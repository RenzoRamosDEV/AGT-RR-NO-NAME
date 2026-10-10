from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from duelo.application.read_models import ChangeCursor, ChangeSummary
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated
from duelo.domain.review_status import ChangeReviewStatus, review_status_of_run
from tests.fakes.event_log import FakeEventLog
from tests.fakes.review_repository import FakeReviewRepository


class FakeChangeRepository:
    """Repositorio en memoria para testear `ingest_change` sin Postgres."""

    def __init__(
        self, reviews: FakeReviewRepository | None = None, events: FakeEventLog | None = None
    ) -> None:
        self._reviews = reviews or FakeReviewRepository()
        self._events = events
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
        self._reviews.register_change(change.id, change.project_id)
        if self._events is not None:
            self._events.append(event, project_id=change.project_id)
        return change

    async def get(self, change_id: UUID) -> Change | None:
        return self._by_id.get(change_id)

    async def advance_run(
        self, change_id: UUID, *, from_run: int, started_at: datetime
    ) -> Change | None:
        change = self._by_id.get(change_id)
        if change is None or change.run != from_run:
            return None
        advanced = replace(change, run=from_run + 1, run_started_at=started_at)
        self._by_id[change_id] = advanced
        self._by_natural_key[(str(change.project_id), change.kind.value, change.head_sha)] = (
            advanced
        )
        return advanced

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        kind: ChangeKind | None,
        status: frozenset[ChangeReviewStatus] | None,
        q: str | None,
        expected_agents: int,
        limit: int,
        after: ChangeCursor | None,
    ) -> list[ChangeSummary]:
        rows = [
            c
            for c in self._by_id.values()
            if c.project_id == project_id
            and (kind is None or c.kind == kind)
            and (q is None or _matches(c, q))
        ]
        rows.sort(key=lambda c: (c.created_at, c.id), reverse=True)
        if after is not None:
            rows = [c for c in rows if (c.created_at, c.id) < (after.created_at, after.id)]
        summaries: list[ChangeSummary] = []
        for c in rows:
            review_status = review_status_of_run(
                c.run, await self._reviews.list_for_change(c.id), expected_agents=expected_agents
            )
            if status and review_status not in status:
                continue
            summaries.append(
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
                    review_status=review_status,
                    run=c.run,
                    created_at=c.created_at,
                    run_started_at=c.run_started_at,
                    diff_summary=c.diff_summary,
                )
            )
        return summaries[:limit]


def _matches(change: Change, q: str) -> bool:
    needle = q.lower()
    return any(
        needle in field.lower()
        for field in (change.title, change.author, change.head_sha, change.ref)
    )
