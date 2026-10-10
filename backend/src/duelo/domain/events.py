from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from duelo.domain.review import Review


@dataclass(frozen=True, slots=True)
class ChangeCreated:
    change_id: UUID
    project_id: UUID
    kind: str
    head_sha: str

    type: str = "change.created"

    def to_payload(self) -> dict[str, Any]:
        return {
            "change_id": str(self.change_id),
            "project_id": str(self.project_id),
            "kind": self.kind,
            "head_sha": self.head_sha,
        }


@dataclass(frozen=True, slots=True)
class CommitDiscarded:
    """El commit ya no es alcanzable desde ninguna referencia del repositorio local."""

    change_id: UUID
    project_id: UUID

    type: str = "commit.discarded"

    def to_payload(self) -> dict[str, Any]:
        return {"change_id": str(self.change_id), "project_id": str(self.project_id)}


@dataclass(frozen=True, slots=True)
class CommitRestored:
    """Un commit que estaba deshecho vuelve a ser alcanzable."""

    change_id: UUID
    project_id: UUID

    type: str = "commit.restored"

    def to_payload(self) -> dict[str, Any]:
        return {"change_id": str(self.change_id), "project_id": str(self.project_id)}


@dataclass(frozen=True, slots=True)
class CommitReverted:
    """Otro commit (`reverted_by_change_id`) revierte este con `git revert`."""

    change_id: UUID
    project_id: UUID
    reverted_by_change_id: UUID

    type: str = "commit.reverted"

    def to_payload(self) -> dict[str, Any]:
        return {
            "change_id": str(self.change_id),
            "project_id": str(self.project_id),
            "reverted_by_change_id": str(self.reverted_by_change_id),
        }


@dataclass(frozen=True, slots=True)
class ReviewCompleted:
    review_id: UUID
    change_id: UUID
    project_id: UUID
    agent: str

    type: str = "review.completed"

    def to_payload(self) -> dict[str, Any]:
        return {
            "review_id": str(self.review_id),
            "change_id": str(self.change_id),
            "project_id": str(self.project_id),
            "agent": self.agent,
        }


@dataclass(frozen=True, slots=True)
class ReviewReused:
    """Una review copiada de otro change (la PR reutiliza las de su commit idéntico)."""

    review_id: UUID
    change_id: UUID
    project_id: UUID
    agent: str
    reused_from_change_id: UUID

    type: str = "review.reused"

    @classmethod
    def of(cls, review: Review, *, project_id: UUID) -> ReviewReused:
        """El evento de una review copiada; falla si la review no es una copia."""
        if review.reused_from_change_id is None:
            raise ValueError("la review no es una copia: no tiene change de origen")
        return cls(
            review_id=review.id,
            change_id=review.change_id,
            project_id=project_id,
            agent=review.agent,
            reused_from_change_id=review.reused_from_change_id,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "review_id": str(self.review_id),
            "change_id": str(self.change_id),
            "project_id": str(self.project_id),
            "agent": self.agent,
            "reused_from_change_id": str(self.reused_from_change_id),
        }


@dataclass(frozen=True, slots=True)
class ReviewFailed:
    review_id: UUID
    change_id: UUID
    project_id: UUID
    agent: str
    error: str

    type: str = "review.failed"

    def to_payload(self) -> dict[str, Any]:
        return {
            "review_id": str(self.review_id),
            "change_id": str(self.change_id),
            "project_id": str(self.project_id),
            "agent": self.agent,
            "error": self.error,
        }
