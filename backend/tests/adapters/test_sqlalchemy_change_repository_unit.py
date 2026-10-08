from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from review_arena.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from review_arena.domain.change import Change, ChangeKind
from review_arena.domain.events import ChangeCreated


def _make_change(project_id, head_sha: str = "a" * 40) -> Change:
    return Change.new(
        project_id=project_id,
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha=head_sha,
        title="fix: algo",
        author="renzo",
        url="https://example.com",
        diff="diff --git a/x b/x",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )


def _fake_session_with(insert_returns: object, select_returns: object) -> MagicMock:
    insert_result = MagicMock()
    insert_result.scalar_one_or_none.return_value = insert_returns

    select_result = MagicMock()
    select_result.scalar_one.return_value = select_returns

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[insert_result, select_result])
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
    return session


async def test_add_returns_existing_change_when_insert_conflicts() -> None:
    """Camino sin fila devuelta: ON CONFLICT DO NOTHING no insertó nada."""
    project_id = uuid4()
    change = _make_change(project_id)
    event = ChangeCreated(
        change_id=change.id,
        project_id=project_id,
        kind=change.kind.value,
        head_sha=change.head_sha,
    )

    existing_row = MagicMock()
    existing_row.id = uuid4()
    existing_row.project_id = project_id
    existing_row.kind = "commit"
    existing_row.ref = change.ref
    existing_row.head_sha = change.head_sha
    existing_row.title = change.title
    existing_row.author = change.author
    existing_row.url = change.url
    existing_row.diff = change.diff
    existing_row.diff_truncated = change.diff_truncated
    existing_row.status = change.status
    existing_row.run = change.run
    existing_row.created_at = change.created_at

    session = _fake_session_with(insert_returns=None, select_returns=existing_row)
    repo = SqlAlchemyChangeRepository(session)

    result = await repo.add(change, event)

    assert result.id == existing_row.id
    assert session.execute.await_count == 2


async def test_add_inserts_event_when_insert_succeeds() -> None:
    """Camino feliz: ON CONFLICT DO NOTHING insertó y devolvió el id nuevo."""
    project_id = uuid4()
    change = _make_change(project_id)
    event = ChangeCreated(
        change_id=change.id,
        project_id=project_id,
        kind=change.kind.value,
        head_sha=change.head_sha,
    )

    insert_result = MagicMock()
    insert_result.scalar_one_or_none.return_value = change.id

    event_insert_result = MagicMock()

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[insert_result, event_insert_result])
    session.begin.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=False)

    repo = SqlAlchemyChangeRepository(session)
    result = await repo.add(change, event)

    assert result is change
    assert session.execute.await_count == 2
