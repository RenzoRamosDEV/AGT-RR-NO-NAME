from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from uuid import UUID

from duelo.application.ports import CommitWithReviews
from duelo.application.read_models import ChangeCursor, ChangeSummary, RevertRef, ReviewBrief
from duelo.domain.change import Change, ChangeKind
from duelo.domain.commit_state import commit_state_of
from duelo.domain.events import ChangeCreated, CommitReverted, ReviewReused
from duelo.domain.review import Review
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

    async def add(
        self,
        change: Change,
        event: ChangeCreated,
        reused: Sequence[tuple[Review, ReviewReused]] = (),
    ) -> Change:
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
        for review, review_event in reused:
            await self._reviews.add(review, review_event)
        self._record_revert(change)
        return change

    def _record_revert(self, change: Change) -> None:
        """`commit.reverted` en la línea de tiempo del original, solo al crear el revert."""
        if change.reverts_sha is None or self._events is None:
            return
        original = self._by_natural_key.get(
            (str(change.project_id), ChangeKind.COMMIT.value, change.reverts_sha)
        )
        if original is not None and original.id != change.id:
            self._events.append(
                CommitReverted(
                    change_id=original.id,
                    project_id=change.project_id,
                    reverted_by_change_id=change.id,
                ),
                project_id=change.project_id,
            )

    async def find_commit_with_reviews(
        self, project_id: UUID, head_sha: str
    ) -> CommitWithReviews | None:
        commit = self._by_natural_key.get((str(project_id), ChangeKind.COMMIT.value, head_sha))
        if commit is None:
            return None
        stored = await self._reviews.list_for_change(commit.id)
        return CommitWithReviews(commit, tuple(r for r in stored if r.run == commit.run))

    async def has_reused_reviews(self, change_id: UUID) -> bool:
        stored = await self._reviews.list_for_change(change_id)
        return any(r.run == 1 and r.reused_from_change_id is not None for r in stored)

    async def get(self, change_id: UUID) -> Change | None:
        return self._by_id.get(change_id)

    async def live_reverter(self, project_id: UUID, head_sha: str) -> RevertRef | None:
        """El revert más reciente que sigue en la rama (los deshechos ya no revierten)."""
        candidates = [
            c
            for c in self._by_id.values()
            if c.project_id == project_id
            and c.kind is ChangeKind.COMMIT
            and c.reverts_sha == head_sha
            and c.discarded_at is None
            and c.head_sha != head_sha
        ]
        if not candidates:
            return None
        newest = max(candidates, key=lambda c: (c.created_at, c.id))
        return RevertRef(id=newest.id, head_sha=newest.head_sha)

    def _store(self, change: Change) -> None:
        """Sustituye un change ya guardado (marcas de estado) en los dos índices."""
        self._by_id[change.id] = change
        self._by_natural_key[(str(change.project_id), change.kind.value, change.head_sha)] = change

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
            reverter = (
                await self.live_reverter(c.project_id, c.head_sha)
                if c.kind is ChangeKind.COMMIT
                else None
            )
            stored = await self._reviews.list_for_change(c.id)
            review_status = review_status_of_run(c.run, stored, expected_agents=expected_agents)
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
                    reviews=tuple(
                        ReviewBrief(
                            agent=r.agent,
                            status=r.status,
                            score=r.score,
                            duration_ms=r.duration_ms,
                            run=r.run,
                            reused_from=r.reused_from_change_id,
                        )
                        for r in sorted(stored, key=lambda r: r.agent)
                        if r.run == c.run
                    ),
                    commit_state=commit_state_of(
                        kind=c.kind, discarded_at=c.discarded_at, reverted=reverter is not None
                    ),
                    reverted_by=reverter,
                )
            )
        return summaries[:limit]

    def mark_discarded(self, change_id: UUID, at: datetime | None) -> None:
        """Atajo de test: pone o quita la marca de deshecho de un change guardado."""
        self._store(replace(self._by_id[change_id], discarded_at=at))


def _matches(change: Change, q: str) -> bool:
    needle = q.lower()
    return any(
        needle in field.lower()
        for field in (change.title, change.author, change.head_sha, change.ref)
    )
