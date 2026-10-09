from uuid import uuid4

import pytest

from duelo.application.ingest_commit import (
    ChangeSubmission,
    ProjectNotFound,
    ingest_commit,
    ingest_pr,
)
from duelo.application.ports import ReviewStartError
from duelo.domain.change import ChangeKind
from duelo.domain.project import Project
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.project_repository import FakeProjectRepository
from tests.fakes.review_starter import FakeReviewStarter

PROJECT = Project(id=uuid4(), slug="acme/widgets")


def _submission(**overrides: object) -> ChangeSubmission:
    values: dict[str, object] = {
        "project": PROJECT.slug,
        "ref": "refs/pull/7/head",
        "head_sha": "b" * 40,
        "title": "feat: algo",
        "author": "renzo",
        "url": "https://example.com/pull/7",
        "diff": "diff --git a/x b/x",
    }
    values.update(overrides)
    return ChangeSubmission(**values)  # type: ignore[arg-type]


def _deps(starter: FakeReviewStarter | None = None):
    return FakeProjectRepository(PROJECT), FakeChangeRepository(), starter or FakeReviewStarter()


async def test_pr_is_persisted_as_kind_pr_and_its_review_started() -> None:
    projects, changes, starter = _deps()

    change = await ingest_pr(projects, changes, starter, _submission(), max_diff_chars=100)

    assert change.kind is ChangeKind.PR
    assert changes.persisted_events[0].kind == "pr"
    assert starter.started[("pr", str(PROJECT.id), "b" * 40, 1)] == change


async def test_resending_a_pr_is_idempotent() -> None:
    projects, changes, starter = _deps()

    first = await ingest_pr(projects, changes, starter, _submission(), max_diff_chars=100)
    second = await ingest_pr(projects, changes, starter, _submission(), max_diff_chars=100)

    assert first.id == second.id
    assert len(changes.persisted_events) == 1 and len(starter.started) == 1


async def test_pr_and_commit_with_the_same_sha_are_distinct_changes_with_their_own_review() -> None:
    projects, changes, starter = _deps()

    commit = await ingest_commit(projects, changes, starter, _submission(), max_diff_chars=100)
    pr = await ingest_pr(projects, changes, starter, _submission(), max_diff_chars=100)

    assert commit.id != pr.id
    assert {k[0] for k in starter.started} == {"commit", "pr"}


async def test_pr_diff_is_cut_like_a_commit_diff() -> None:
    projects, changes, starter = _deps()

    change = await ingest_pr(
        projects, changes, starter, _submission(diff="x" * 11), max_diff_chars=10
    )

    assert change.diff == "x" * 10 and change.diff_truncated is True


async def test_unknown_project_has_no_effects() -> None:
    projects, changes, starter = _deps()

    with pytest.raises(ProjectNotFound):
        await ingest_pr(
            projects, changes, starter, _submission(project="otro/repo"), max_diff_chars=100
        )

    assert changes.persisted_events == [] and starter.calls == 0


async def test_starter_failure_keeps_the_pr_and_a_retry_recovers() -> None:
    projects, changes, _ = _deps()

    with pytest.raises(ReviewStartError):
        await ingest_pr(
            projects, changes, FakeReviewStarter(fail=True), _submission(), max_diff_chars=100
        )
    working = FakeReviewStarter()
    change = await ingest_pr(projects, changes, working, _submission(), max_diff_chars=100)

    assert len(changes.persisted_events) == 1
    assert working.started[("pr", str(PROJECT.id), "b" * 40, 1)] == change
