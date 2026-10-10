from __future__ import annotations

from uuid import UUID

from duelo.application.read_models import AgentStats
from duelo.domain.events import ReviewCompleted, ReviewFailed, ReviewReused
from duelo.domain.review import Review, ReviewStatus
from tests.fakes.event_log import FakeEventLog


class FakeReviewRepository:
    """Repositorio en memoria para testear `record_review` sin Postgres."""

    def __init__(self, events: FakeEventLog | None = None) -> None:
        self._by_natural_key: dict[tuple[str, str, int], Review] = {}
        self._project_of_change: dict[UUID, UUID] = {}
        self._events = events
        self.persisted_events: list[ReviewCompleted | ReviewFailed | ReviewReused] = []

    def register_change(self, change_id: UUID, project_id: UUID) -> None:
        """El repositorio de changes avisa de a qué proyecto pertenece cada change: hace falta
        para filtrar las estadísticas por proyecto, como el JOIN del adaptador real."""
        self._project_of_change[change_id] = project_id

    async def add(
        self, review: Review, event: ReviewCompleted | ReviewFailed | ReviewReused
    ) -> Review:
        key = (str(review.change_id), review.agent, review.run)
        existing = self._by_natural_key.get(key)
        if existing is not None:
            return existing

        self._by_natural_key[key] = review
        self.persisted_events.append(event)
        if self._events is not None:
            self._events.append(event, project_id=event.project_id)
        return review

    async def get(self, review_id: UUID) -> Review | None:
        return next((r for r in self._by_natural_key.values() if r.id == review_id), None)

    async def list_for_change(self, change_id: UUID) -> list[Review]:
        rows = [r for r in self._by_natural_key.values() if r.change_id == change_id]
        return sorted(rows, key=lambda r: (r.created_at, r.agent, r.run))

    async def agent_stats(self, *, project_id: UUID | None) -> list[AgentStats]:
        stats: list[AgentStats] = []
        scoped = [
            r
            for r in self._by_natural_key.values()
            if project_id is None or self._project_of_change.get(r.change_id) == project_id
        ]
        for agent in sorted({r.agent for r in scoped}):
            rows = [r for r in scoped if r.agent == agent]
            durations = [r.duration_ms for r in rows if r.duration_ms is not None]
            scores = [r.score for r in rows if r.score is not None]
            stats.append(
                AgentStats(
                    agent=agent,
                    total=len(rows),
                    completed=sum(r.status is ReviewStatus.COMPLETED for r in rows),
                    failed=sum(r.status is ReviewStatus.FAILED for r in rows),
                    avg_duration_ms=sum(durations) / len(durations) if durations else None,
                    avg_score=sum(scores) / len(scores) if scores else None,
                )
            )
        return stats
