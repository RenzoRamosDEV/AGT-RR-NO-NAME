from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from review_arena.application.ports import ChangeRepository
from review_arena.domain.change import Change, ChangeKind
from review_arena.domain.events import ChangeCreated


async def ingest_change(
    repository: ChangeRepository,
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
) -> Change:
    change = Change.new(
        project_id=project_id,
        kind=kind,
        ref=ref,
        head_sha=head_sha,
        title=title,
        author=author,
        url=url,
        diff=diff,
        diff_truncated=diff_truncated,
        created_at=datetime.now(UTC),
    )
    event = ChangeCreated(
        change_id=change.id,
        project_id=change.project_id,
        kind=change.kind.value,
        head_sha=change.head_sha,
    )
    return await repository.add(change, event)
