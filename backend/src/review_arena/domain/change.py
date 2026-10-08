from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class ChangeKind(StrEnum):
    COMMIT = "commit"
    PR = "pr"


class ChangeStatus(StrEnum):
    PENDING = "pending"


@dataclass(frozen=True, slots=True)
class Change:
    id: UUID
    project_id: UUID
    kind: ChangeKind
    ref: str
    head_sha: str
    title: str
    author: str
    url: str
    diff: str
    diff_truncated: bool
    status: ChangeStatus
    run: int
    created_at: datetime

    @classmethod
    def new(
        cls,
        *,
        project_id: UUID,
        kind: ChangeKind,
        ref: str,
        head_sha: str,
        title: str,
        author: str,
        url: str,
        diff: str,
        diff_truncated: bool,
        created_at: datetime,
    ) -> Change:
        if not head_sha:
            raise ValueError("head_sha no puede estar vacío")
        return cls(
            id=uuid4(),
            project_id=project_id,
            kind=kind,
            ref=ref,
            head_sha=head_sha,
            title=title,
            author=author,
            url=url,
            diff=diff,
            diff_truncated=diff_truncated,
            status=ChangeStatus.PENDING,
            run=1,
            created_at=created_at,
        )
