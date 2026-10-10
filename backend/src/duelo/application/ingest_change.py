from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from duelo.application.ports import ChangeRepository
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewReused
from duelo.domain.review_reuse import reviews_to_reuse


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
    agent_names: Sequence[str] = (),
    reverts_sha: str | None = None,
) -> Change:
    """Persiste el change. `change_id` fija el id del candidato: si el repositorio devuelve un
    change con otro id, ya existía (la identidad natural es otra).

    Una PR (con `agent_names`, los agentes esperados) nace con las reviews copiadas de su commit
    idéntico cuando todos las completaron: se guardan en la misma transacción que el change."""
    now = datetime.now(UTC)
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
        created_at=now,
        id=change_id,
        reverts_sha=reverts_sha,
    )
    event = ChangeCreated(
        change_id=change.id,
        project_id=change.project_id,
        kind=change.kind.value,
        head_sha=change.head_sha,
    )
    if kind is not ChangeKind.PR or not agent_names:
        return await repository.add(change, event)

    source = await repository.find_commit_with_reviews(project_id, head_sha)
    copies = reviews_to_reuse(
        change,
        source.change if source else None,
        source.reviews if source else (),
        agent_names=agent_names,
        now=now,
    )
    return await repository.add(
        change, event, [(c, ReviewReused.of(c, project_id=project_id)) for c in copies]
    )
