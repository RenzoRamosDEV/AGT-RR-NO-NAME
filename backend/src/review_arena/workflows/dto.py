"""DTOs serializables para cruzar el límite de Temporal (workflows/activities no
reciben entidades de dominio directamente - ver openspec/config.yaml: 'workflows y
activities reciben IDs, no datos')."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from review_arena.domain.change import Change, ChangeKind


@dataclass
class ChangeDTO:
    id: str
    project_id: str
    kind: str
    ref: str
    head_sha: str
    title: str
    author: str
    url: str
    diff: str
    diff_truncated: bool
    status: str
    run: int
    created_at: str

    @classmethod
    def from_domain(cls, change: Change) -> ChangeDTO:
        return cls(
            id=str(change.id),
            project_id=str(change.project_id),
            kind=change.kind.value,
            ref=change.ref,
            head_sha=change.head_sha,
            title=change.title,
            author=change.author,
            url=change.url,
            diff=change.diff,
            diff_truncated=change.diff_truncated,
            status=change.status,
            run=change.run,
            created_at=change.created_at.isoformat(),
        )

    def to_domain(self) -> Change:
        return Change(
            id=UUID(self.id),
            project_id=UUID(self.project_id),
            kind=ChangeKind(self.kind),
            ref=self.ref,
            head_sha=self.head_sha,
            title=self.title,
            author=self.author,
            url=self.url,
            diff=self.diff,
            diff_truncated=self.diff_truncated,
            status=self.status,
            run=self.run,
            created_at=datetime.fromisoformat(self.created_at),
        )


@dataclass
class RunReviewInput:
    change: ChangeDTO
    agent_name: str
    run: int


@dataclass
class RunReviewResult:
    status: str
    review_id: str
