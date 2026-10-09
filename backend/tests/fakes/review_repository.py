from __future__ import annotations

from uuid import UUID

from duelo.application.read_models import AgentStats
from duelo.domain.events import ReviewCompleted, ReviewFailed
from duelo.domain.review import Review, ReviewStatus


class FakeReviewRepository:
    """Repositorio en memoria para testear `record_review` sin Postgres."""

    def __init__(self) -> None:
        self._by_natural_key: dict[tuple[str, str, int], Review] = {}
        self.persisted_events: list[ReviewCompleted | ReviewFailed] = []

    async def add(self, review: Review, event: ReviewCompleted | ReviewFailed) -> Review:
        key = (str(review.change_id), review.agent, review.run)
        existing = self._by_natural_key.get(key)
        if existing is not None:
            return existing

        self._by_natural_key[key] = review
        self.persisted_events.append(event)
        return review

    async def list_for_change(self, change_id: UUID) -> list[Review]:
        rows = [r for r in self._by_natural_key.values() if r.change_id == change_id]
        return sorted(rows, key=lambda r: (r.created_at, r.agent, r.run))

    async def agent_stats(self) -> list[AgentStats]:
        stats: list[AgentStats] = []
        for agent in sorted({r.agent for r in self._by_natural_key.values()}):
            rows = [r for r in self._by_natural_key.values() if r.agent == agent]
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
