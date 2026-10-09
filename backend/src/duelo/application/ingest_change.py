from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from duelo.application.ports import ChangeRepository
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated


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
    change_id: UUID | None = None,
) -> Change:
    """Persiste el change. `change_id` fija el id del candidato: si el repositorio devuelve un
    change con otro id, ya existía (la identidad natural es otra)."""
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
        id=change_id,
    )
    event = ChangeCreated(
        change_id=change.id,
        project_id=change.project_id,
        kind=change.kind.value,
        head_sha=change.head_sha,
    )
    return await repository.add(change, event)
