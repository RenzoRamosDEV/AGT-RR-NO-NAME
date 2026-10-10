"""`get_change_detail` y el estado de un commit: activo, deshecho o revertido, y el commit que lo
revierte. La lista de changes se cubre en `test_commit_state_api.py` y en los tests de integración;
estos son los casos de la capa de aplicación (los que ejecuta la mutación)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from duelo.application.queries import get_change_detail
from duelo.application.read_models import ChangeDetail
from duelo.domain.change import Change, ChangeKind
from duelo.domain.commit_state import CommitState
from duelo.domain.events import ChangeCreated
from duelo.domain.project import Project
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.review_repository import FakeReviewRepository

PROJECT = Project(id=uuid4(), slug="acme/widgets")
T0 = datetime(2026, 1, 1, tzinfo=UTC)
SHA_A, SHA_B, SHA_C = "a" * 40, "b" * 40, "c" * 40


class Fixture:
    def __init__(self) -> None:
        self.changes = FakeChangeRepository()
        self.reviews = FakeReviewRepository()

    async def add(
        self,
        sha: str,
        *,
        kind: ChangeKind = ChangeKind.COMMIT,
        reverts: str | None = None,
        at: datetime = T0,
    ) -> Change:
        change = Change.new(
            project_id=PROJECT.id,
            kind=kind,
            ref="main",
            head_sha=sha,
            title="t",
            author="a",
            url="",
            diff="",
            diff_truncated=False,
            created_at=at,
            reverts_sha=reverts,
        )
        event = ChangeCreated(
            change_id=change.id, project_id=PROJECT.id, kind=kind.value, head_sha=sha
        )
        return await self.changes.add(change, event)

    async def detail(self, change_id: UUID) -> ChangeDetail:
        found = await get_change_detail(
            self.changes,
            self.reviews,
            change_id,
            expected_agents=2,
            now=T0,
            stale_after=timedelta(hours=1),
        )
        assert found is not None
        return found


async def test_a_normal_commit_is_active_and_has_no_reverter() -> None:
    f = Fixture()
    change = await f.add(SHA_A)

    detail = await f.detail(change.id)

    assert detail.commit_state is CommitState.ACTIVE
    assert detail.reverted_by is None


async def test_a_discarded_commit_is_discarded() -> None:
    f = Fixture()
    change = await f.add(SHA_A)
    f.changes.mark_discarded(change.id, T0)

    detail = await f.detail(change.id)

    assert detail.commit_state is CommitState.DISCARDED
    assert detail.reverted_by is None


async def test_a_reverted_commit_names_the_commit_that_reverts_it() -> None:
    f = Fixture()
    original = await f.add(SHA_A)
    revert = await f.add(SHA_B, reverts=SHA_A)

    detail = await f.detail(original.id)

    assert detail.commit_state is CommitState.REVERTED
    assert detail.reverted_by is not None
    assert (detail.reverted_by.id, detail.reverted_by.head_sha) == (revert.id, SHA_B)


async def test_the_commit_that_reverts_is_itself_active() -> None:
    f = Fixture()
    await f.add(SHA_A)
    revert = await f.add(SHA_B, reverts=SHA_A)

    detail = await f.detail(revert.id)

    assert detail.commit_state is CommitState.ACTIVE
    assert detail.reverted_by is None


async def test_discarded_wins_over_reverted_but_keeps_the_reverter() -> None:
    f = Fixture()
    original = await f.add(SHA_A)
    revert = await f.add(SHA_B, reverts=SHA_A)
    f.changes.mark_discarded(original.id, T0)

    detail = await f.detail(original.id)

    assert detail.commit_state is CommitState.DISCARDED
    assert detail.reverted_by is not None and detail.reverted_by.id == revert.id


async def test_an_undone_revert_no_longer_reverts() -> None:
    f = Fixture()
    original = await f.add(SHA_A)
    revert = await f.add(SHA_B, reverts=SHA_A)
    f.changes.mark_discarded(revert.id, T0)

    detail = await f.detail(original.id)

    assert detail.commit_state is CommitState.ACTIVE
    assert detail.reverted_by is None


async def test_the_newest_live_revert_is_the_one_shown() -> None:
    f = Fixture()
    original = await f.add(SHA_A)
    await f.add(SHA_B, reverts=SHA_A, at=T0 + timedelta(minutes=1))
    newest = await f.add(SHA_C, reverts=SHA_A, at=T0 + timedelta(minutes=2))

    detail = await f.detail(original.id)

    assert detail.reverted_by is not None and detail.reverted_by.id == newest.id


async def test_a_pr_is_always_active_even_if_a_commit_has_its_sha_reverted() -> None:
    f = Fixture()
    pr = await f.add(SHA_A, kind=ChangeKind.PR)
    await f.add(SHA_B, reverts=SHA_A)  # revierte un SHA que en este proyecto solo es de una PR
    f.changes.mark_discarded(pr.id, T0)

    detail = await f.detail(pr.id)

    assert detail.commit_state is CommitState.ACTIVE
    assert detail.reverted_by is None
