from uuid import uuid4

from review_arena.application.ingest_change import ingest_change
from review_arena.domain.change import ChangeKind
from tests.fakes.change_repository import FakeChangeRepository


async def test_get_returns_none_for_unknown_id() -> None:
    repo = FakeChangeRepository()

    assert await repo.get(uuid4()) is None


async def test_get_returns_the_persisted_change() -> None:
    repo = FakeChangeRepository()
    project_id = uuid4()

    created = await ingest_change(
        repo,
        project_id=project_id,
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha="a" * 40,
        title="fix: algo",
        author="renzo",
        url="https://example.com",
        diff="diff --git a/x b/x",
        diff_truncated=False,
    )

    fetched = await repo.get(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.head_sha == "a" * 40
