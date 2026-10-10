"""Un commit que revierte a otro (`git revert`) guarda el SHA que revierte: el original está
revertido mientras algún commit de revert siga en la rama, llegue en el orden que llegue."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from duelo.application.ingest_commit import ChangeSubmission, ingest_commit, ingest_pr
from duelo.domain.commit_state import CommitState, commit_state_of
from duelo.domain.project import Project
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.event_log import FakeChangeEventRepository, FakeEventLog
from tests.fakes.project_repository import FakeProjectRepository
from tests.fakes.review_repository import FakeReviewRepository
from tests.fakes.review_starter import FakeReviewStarter

SHA_A, SHA_B, SHA_C = "a" * 40, "b" * 40, "c" * 40
PROJECT = Project(id=uuid4(), slug="acme/widgets")
NOW = datetime(2026, 1, 1, tzinfo=UTC)


class Fixture:
    def __init__(self) -> None:
        self.events = FakeEventLog()
        self.changes = FakeChangeRepository(FakeReviewRepository(self.events), self.events)
        self.projects = FakeProjectRepository(PROJECT)
        self.starter = FakeReviewStarter()

    async def commit(self, sha: str, *, title: str = "feat: algo", body: str = "") -> UUID:
        result = await ingest_commit(
            self.projects,
            self.changes,
            self.starter,
            ChangeSubmission(
                project=PROJECT.slug,
                ref="main",
                head_sha=sha,
                title=title,
                author="ana",
                url="",
                diff="",
                body=body,
            ),
            max_diff_chars=1000,
        )
        return result.change.id

    async def state(self, change_id: UUID) -> CommitState:
        change = await self.changes.get(change_id)
        assert change is not None
        reverter = await self.changes.live_reverter(change.project_id, change.head_sha)
        return commit_state_of(
            kind=change.kind, discarded_at=change.discarded_at, reverted=reverter is not None
        )

    async def reverter(self, change_id: UUID) -> UUID | None:
        change = await self.changes.get(change_id)
        assert change is not None
        ref = await self.changes.live_reverter(change.project_id, change.head_sha)
        return ref.id if ref else None

    async def event_types(self, change_id: UUID) -> list[str]:
        events = FakeChangeEventRepository(self.events)
        return [e.type for e in await events.list_for_change(PROJECT.id, change_id)]

    def discard(self, change_id: UUID, *, at: datetime | None = NOW) -> None:
        self.changes.mark_discarded(change_id, at)


def _revert_message(sha: str) -> str:
    return f"This reverts commit {sha}.\n\nRompe el login."


async def test_a_revert_marks_the_original_commit_as_reverted() -> None:
    f = Fixture()
    original = await f.commit(SHA_A)

    revert = await f.commit(SHA_B, title='Revert "feat: algo"', body=_revert_message(SHA_A))

    assert await f.state(original) is CommitState.REVERTED
    assert await f.reverter(original) == revert
    assert await f.state(revert) is CommitState.ACTIVE
    assert await f.event_types(original) == ["change.created", "commit.reverted"]


async def test_the_revert_stores_the_sha_it_reverts_and_not_the_message() -> None:
    f = Fixture()

    revert = await f.commit(SHA_B, body=_revert_message(SHA_A.upper()))

    stored = await f.changes.get(revert)
    assert stored is not None
    assert stored.reverts_sha == SHA_A  # en minúsculas
    assert SHA_A not in stored.title  # el cuerpo no se guarda


async def test_resending_the_revert_does_not_repeat_the_event_or_change_the_state() -> None:
    f = Fixture()
    original = await f.commit(SHA_A)
    revert = await f.commit(SHA_B, body=_revert_message(SHA_A))

    again = await f.commit(SHA_B, body=_revert_message(SHA_A))

    assert again == revert
    assert await f.reverter(original) == revert
    assert await f.event_types(original) == ["change.created", "commit.reverted"]


async def test_a_revert_that_arrives_before_the_original_still_reverts_it() -> None:
    """El dato vive en el commit de revert: da igual el orden en que lleguen a Duelo (p. ej. si el
    hook del original falló y lo recuperó el `pre-push` después)."""
    f = Fixture()
    revert = await f.commit(SHA_B, body=_revert_message(SHA_A))

    original = await f.commit(SHA_A)

    assert await f.state(original) is CommitState.REVERTED
    assert await f.reverter(original) == revert


async def test_a_revert_of_a_commit_duelo_does_not_know_is_not_an_error() -> None:
    f = Fixture()

    revert = await f.commit(SHA_B, body=_revert_message(SHA_A))

    assert await f.state(revert) is CommitState.ACTIVE
    assert f.starter.started  # el commit se ingirió y se revisa con normalidad


async def test_a_revert_does_not_touch_a_commit_of_another_project() -> None:
    f = Fixture()
    other = Project(id=uuid4(), slug="acme/other")
    f.projects = FakeProjectRepository(PROJECT, other)
    mine = await f.commit(SHA_A)

    await ingest_commit(
        f.projects,
        f.changes,
        f.starter,
        ChangeSubmission(
            project=other.slug,
            ref="main",
            head_sha=SHA_C,
            title="t",
            author="a",
            url="",
            diff="",
            body=_revert_message(SHA_A),
        ),
        max_diff_chars=1000,
    )

    assert await f.state(mine) is CommitState.ACTIVE


async def test_when_two_commits_revert_it_the_newest_counts_and_the_other_takes_over() -> None:
    f = Fixture()
    original = await f.commit(SHA_A)
    first = await f.commit(SHA_B, body=_revert_message(SHA_A))
    second = await f.commit(SHA_C, body=_revert_message(SHA_A))

    assert await f.reverter(original) == second

    f.discard(second)  # el segundo revert se deshace: el primero sigue valiendo
    assert await f.reverter(original) == first
    assert await f.state(original) is CommitState.REVERTED


async def test_an_undone_revert_leaves_the_original_active_until_it_comes_back() -> None:
    f = Fixture()
    original = await f.commit(SHA_A)
    revert = await f.commit(SHA_B, body=_revert_message(SHA_A))

    f.discard(revert)
    assert await f.state(original) is CommitState.ACTIVE
    assert await f.reverter(original) is None

    f.discard(revert, at=None)  # `git reset` de vuelta
    assert await f.state(original) is CommitState.REVERTED


@pytest.mark.parametrize("discard_before_new_arrives", [True, False])
async def test_an_amended_revert_is_replaced_by_the_new_one_in_either_order(
    discard_before_new_arrives: bool,
) -> None:
    """`git commit --amend` sobre el revert deja otro SHA con el mismo mensaje. La API lo ingiere al
    instante y el barrido marca el antiguo como deshecho cuando le toca: el resultado es el mismo
    llegue antes uno u otro."""
    f = Fixture()
    original = await f.commit(SHA_A)
    old = await f.commit(SHA_B, body=_revert_message(SHA_A))

    if discard_before_new_arrives:
        f.discard(old)
    new = await f.commit(SHA_C, body=_revert_message(SHA_A))
    if not discard_before_new_arrives:
        f.discard(old)

    assert await f.state(original) is CommitState.REVERTED
    assert await f.reverter(original) == new


async def test_a_revert_message_without_the_sha_marks_nothing() -> None:
    f = Fixture()
    original = await f.commit(SHA_A)

    await f.commit(SHA_B, title='Revert "feat: algo"', body="Lo quito.")

    assert await f.state(original) is CommitState.ACTIVE


async def test_a_commit_that_names_itself_does_not_revert_anything() -> None:
    f = Fixture()

    own = await f.commit(SHA_A, body=_revert_message(SHA_A))

    stored = await f.changes.get(own)
    assert stored is not None and stored.reverts_sha is None
    assert await f.state(own) is CommitState.ACTIVE


async def test_the_sha_can_come_in_the_title() -> None:
    f = Fixture()
    original = await f.commit(SHA_A)

    await f.commit(SHA_B, title=f"This reverts commit {SHA_A}")

    assert await f.state(original) is CommitState.REVERTED


async def test_a_client_that_sends_no_body_keeps_working() -> None:
    f = Fixture()

    change = await f.commit(SHA_A)

    stored = await f.changes.get(change)
    assert stored is not None and stored.reverts_sha is None
    assert await f.state(change) is CommitState.ACTIVE


async def test_a_pr_never_reverts_anything() -> None:
    f = Fixture()
    original = await f.commit(SHA_A)

    result = await ingest_pr(
        f.projects,
        f.changes,
        f.starter,
        ChangeSubmission(
            project=PROJECT.slug,
            ref="x",
            head_sha=SHA_B,
            title="t",
            author="a",
            url="",
            diff="",
            body=_revert_message(SHA_A),
        ),
        max_diff_chars=1000,
    )

    assert result.change.reverts_sha is None
    assert await f.state(original) is CommitState.ACTIVE
