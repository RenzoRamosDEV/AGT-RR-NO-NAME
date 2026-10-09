from __future__ import annotations

from duelo.domain.events import ReviewCompleted, ReviewFailed
from duelo.domain.review import Review


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
