from uuid import uuid4

from review_arena.application.ingest_change import ingest_change
from review_arena.domain.change import ChangeKind
from tests.fakes.change_repository import FakeChangeRepository


async def _ingest(
    repo: FakeChangeRepository,
    *,
    project_id,
    head_sha: str = "a" * 40,
    kind: ChangeKind = ChangeKind.COMMIT,
):
    return await ingest_change(
        repo,
        project_id=project_id,
        kind=kind,
        ref="refs/heads/main",
        head_sha=head_sha,
        title="fix: algo",
        author="renzo",
        url="https://github.com/example/repo/commit/" + head_sha,
        diff="diff --git a/x b/x",
        diff_truncated=False,
    )


async def test_ingest_change_persists_change_and_exactly_one_event() -> None:
    repo = FakeChangeRepository()
    project_id = uuid4()

    change = await _ingest(repo, project_id=project_id)

    assert change.project_id == project_id
    assert len(repo.persisted_events) == 1
    assert repo.persisted_events[0].change_id == change.id


async def test_reingesting_same_natural_key_is_idempotent() -> None:
    repo = FakeChangeRepository()
    project_id = uuid4()

    first = await _ingest(repo, project_id=project_id, head_sha="b" * 40)
    second = await _ingest(repo, project_id=project_id, head_sha="b" * 40)

    assert first.id == second.id
    assert len(repo.persisted_events) == 1


async def test_same_head_sha_in_different_projects_are_independent() -> None:
    repo = FakeChangeRepository()
    head_sha = "c" * 40

    first = await _ingest(repo, project_id=uuid4(), head_sha=head_sha)
    second = await _ingest(repo, project_id=uuid4(), head_sha=head_sha)

    assert first.id != second.id
    assert len(repo.persisted_events) == 2
