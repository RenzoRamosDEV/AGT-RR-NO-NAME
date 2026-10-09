from uuid import uuid4

import pytest

from duelo.application.ingest_commit import CommitSubmission, ProjectNotFound, ingest_commit
from duelo.application.ports import ReviewStartError
from duelo.domain.project import Project
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.project_repository import FakeProjectRepository
from tests.fakes.review_starter import FakeReviewStarter

PROJECT = Project(id=uuid4(), slug="acme/widgets")


def _submission(**overrides: object) -> CommitSubmission:
    values: dict[str, object] = {
        "project": PROJECT.slug,
        "ref": "refs/heads/main",
        "head_sha": "a" * 40,
        "title": "fix: algo",
        "author": "renzo",
        "url": "https://example.com/c/1",
        "diff": "diff --git a/x b/x",
    }
    values.update(overrides)
    return CommitSubmission(**values)  # type: ignore[arg-type]


def _deps(starter: FakeReviewStarter | None = None):
    return (
        FakeProjectRepository(PROJECT),
        FakeChangeRepository(),
        starter or FakeReviewStarter(),
    )


async def test_valid_commit_is_persisted_and_its_review_started() -> None:
    projects, changes, starter = _deps()

    change = await ingest_commit(projects, changes, starter, _submission(), max_diff_chars=100)

    assert change.project_id == PROJECT.id
    assert change.diff_truncated is False
    assert changes.persisted_events and starter.calls == 1
    assert starter.started[(str(PROJECT.id), "a" * 40)] == change


async def test_unknown_project_has_no_effects() -> None:
    projects, changes, starter = _deps()

    with pytest.raises(ProjectNotFound) as error:
        await ingest_commit(
            projects, changes, starter, _submission(project="otro/repo"), max_diff_chars=100
        )

    assert error.value.slug == "otro/repo"
    assert "otro/repo" in str(error.value)
    assert changes.persisted_events == [] and starter.calls == 0


@pytest.mark.parametrize(
    ("diff", "expected", "truncated"),
    [
        ("x" * 9, "x" * 9, False),
        ("x" * 10, "x" * 10, False),  # justo en el límite: no se recorta
        ("x" * 11, "x" * 10, True),
        ("x" * 500, "x" * 10, True),
    ],
)
async def test_diff_is_cut_at_the_limit_and_flagged(
    diff: str, expected: str, truncated: bool
) -> None:
    projects, changes, starter = _deps()

    change = await ingest_commit(
        projects, changes, starter, _submission(diff=diff), max_diff_chars=10
    )

    assert change.diff == expected
    assert change.diff_truncated is truncated


async def test_reingesting_returns_the_same_change_without_duplicating_the_event() -> None:
    projects, changes, starter = _deps()

    first = await ingest_commit(projects, changes, starter, _submission(), max_diff_chars=100)
    second = await ingest_commit(projects, changes, starter, _submission(), max_diff_chars=100)

    assert first.id == second.id
    assert len(changes.persisted_events) == 1
    assert len(starter.started) == 1  # el starter se invoca, pero deduplica por commit


async def test_starter_failure_leaves_the_change_persisted_and_retry_recovers() -> None:
    projects, changes, _ = _deps()
    failing = FakeReviewStarter(fail=True)

    with pytest.raises(ReviewStartError):
        await ingest_commit(projects, changes, failing, _submission(), max_diff_chars=100)
    assert len(changes.persisted_events) == 1 and failing.started == {}

    working = FakeReviewStarter()
    change = await ingest_commit(projects, changes, working, _submission(), max_diff_chars=100)

    assert len(changes.persisted_events) == 1  # no se duplicó el Change
    assert working.started[(str(PROJECT.id), "a" * 40)] == change


async def test_invalid_input_is_rejected_before_starting_a_review() -> None:
    projects, changes, starter = _deps()

    with pytest.raises(ValueError, match="head_sha"):
        await ingest_commit(
            projects, changes, starter, _submission(head_sha=""), max_diff_chars=100
        )

    assert changes.persisted_events == [] and starter.calls == 0
