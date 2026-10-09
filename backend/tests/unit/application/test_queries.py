import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from duelo.application.ingest_commit import ProjectNotFound
from duelo.application.queries import agent_stats, get_change_detail, list_changes, list_projects
from duelo.application.read_models import ChangeCursor
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.project import Project
from duelo.domain.review import Review, ReviewResult
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.project_repository import FakeProjectRepository
from tests.fakes.review_repository import FakeReviewRepository

PROJECT = Project(id=uuid4(), slug="acme/widgets")
T0 = datetime(2026, 1, 1, tzinfo=UTC)


async def _add(
    repo: FakeChangeRepository,
    sha: str,
    *,
    at: datetime,
    kind: ChangeKind = ChangeKind.COMMIT,
    project: Project = PROJECT,
) -> Change:
    change = Change.new(
        project_id=project.id,
        kind=kind,
        ref="refs/heads/main",
        head_sha=sha,
        title=f"change {sha}",
        author="renzo",
        url="https://example.com",
        diff="diff --git a/x b/x",
        diff_truncated=False,
        created_at=at,
    )
    event = ChangeCreated(change_id=change.id, project_id=project.id, kind=kind.value, head_sha=sha)
    return await repo.add(change, event)


async def _walk(
    projects: FakeProjectRepository,
    changes: FakeChangeRepository,
    *,
    limit: int,
    kind: ChangeKind | None = None,
) -> list[list[UUID]]:
    pages: list[list[UUID]] = []
    after: ChangeCursor | None = None
    while True:
        page = await list_changes(
            projects, changes, slug=PROJECT.slug, kind=kind, limit=limit, after=after
        )
        pages.append([c.id for c in page.items])
        if page.next_cursor is None:
            return pages
        after = page.next_cursor


async def test_list_projects_returns_them_sorted_by_slug() -> None:
    b, a = Project(id=uuid4(), slug="b/repo"), Project(id=uuid4(), slug="a/repo")

    assert await list_projects(FakeProjectRepository(b, a)) == [a, b]
    assert await list_projects(FakeProjectRepository()) == []


async def test_channel_is_newest_first_and_ties_are_broken_by_id() -> None:
    projects, changes = FakeProjectRepository(PROJECT), FakeChangeRepository()
    old = await _add(changes, "1" * 40, at=T0)
    tied = [await _add(changes, f"{i}" * 40, at=T0 + timedelta(hours=1)) for i in (2, 3)]
    new = await _add(changes, "4" * 40, at=T0 + timedelta(hours=2))

    (page,) = await _walk(projects, changes, limit=10)

    expected_tied = [c.id for c in sorted(tied, key=lambda c: c.id, reverse=True)]
    assert page == [new.id, *expected_tied, old.id]


@pytest.mark.parametrize(
    ("total", "limit", "pages"),
    [(5, 2, [2, 2, 1]), (4, 2, [2, 2]), (2, 2, [2]), (1, 2, [1]), (0, 2, [0])],
)
async def test_pagination_only_gives_a_cursor_when_more_items_remain(
    total: int, limit: int, pages: list[int]
) -> None:
    projects, changes = FakeProjectRepository(PROJECT), FakeChangeRepository()
    for i in range(total):
        await _add(changes, f"{i:040d}", at=T0 + timedelta(minutes=i))

    walked = await _walk(projects, changes, limit=limit)

    assert [len(p) for p in walked] == pages


@settings(max_examples=60, deadline=None)
@given(
    offsets=st.lists(st.integers(0, 5), max_size=25),
    limit=st.integers(1, 7),
)
def test_walking_every_page_returns_each_change_once_in_order(
    offsets: list[int], limit: int
) -> None:
    """Propiedad: con empates de `created_at` incluidos, paginar nunca repite ni salta."""

    async def scenario() -> tuple[list[UUID], list[UUID]]:
        projects, changes = FakeProjectRepository(PROJECT), FakeChangeRepository()
        for i, offset in enumerate(offsets):
            await _add(changes, f"{i:040d}", at=T0 + timedelta(minutes=offset))
        walked = [cid for page in await _walk(projects, changes, limit=limit) for cid in page]
        everything = await changes.list_for_project(PROJECT.id, kind=None, limit=1000, after=None)
        return walked, [c.id for c in everything]

    walked, everything = asyncio.run(scenario())

    assert walked == everything
    assert len(set(walked)) == len(offsets)


async def test_kind_filter_only_returns_that_kind() -> None:
    projects, changes = FakeProjectRepository(PROJECT), FakeChangeRepository()
    await _add(changes, "1" * 40, at=T0, kind=ChangeKind.COMMIT)
    pr = await _add(changes, "2" * 40, at=T0 + timedelta(minutes=1), kind=ChangeKind.PR)

    assert await _walk(projects, changes, limit=10, kind=ChangeKind.PR) == [[pr.id]]


async def test_other_projects_are_not_listed() -> None:
    other = Project(id=uuid4(), slug="other/repo")
    projects, changes = FakeProjectRepository(PROJECT, other), FakeChangeRepository()
    await _add(changes, "1" * 40, at=T0, project=other)

    assert await _walk(projects, changes, limit=10) == [[]]


async def test_next_cursor_points_at_the_last_returned_item() -> None:
    projects, changes = FakeProjectRepository(PROJECT), FakeChangeRepository()
    for i in range(3):
        await _add(changes, f"{i:040d}", at=T0 + timedelta(minutes=i))

    page = await list_changes(projects, changes, slug=PROJECT.slug, kind=None, limit=2, after=None)

    assert page.next_cursor == ChangeCursor(
        created_at=page.items[-1].created_at, id=page.items[-1].id
    )


async def test_unknown_project_is_reported() -> None:
    with pytest.raises(ProjectNotFound) as error:
        await list_changes(
            FakeProjectRepository(),
            FakeChangeRepository(),
            slug="no/existe",
            kind=None,
            limit=5,
            after=None,
        )

    assert error.value.slug == "no/existe"


def _review(change: Change, agent: str, *, score: int | None, ms: int | None, fail: bool) -> Review:
    if fail:
        return Review.failed(
            change_id=change.id, agent=agent, run=1, error="boom", duration_ms=ms, created_at=T0
        )
    return Review.succeeded(
        change_id=change.id,
        agent=agent,
        run=1,
        result=ReviewResult(summary="ok", score=score),
        raw_output=None,
        duration_ms=ms or 0,
        created_at=T0,
    )


async def _persist(reviews: FakeReviewRepository, review: Review, project: Project) -> None:
    ids = {
        "review_id": review.id,
        "change_id": review.change_id,
        "project_id": project.id,
        "agent": review.agent,
    }
    event = ReviewFailed(**ids, error=review.error) if review.error else ReviewCompleted(**ids)
    await reviews.add(review, event)


async def test_change_detail_has_the_change_and_only_its_reviews() -> None:
    changes, reviews = FakeChangeRepository(), FakeReviewRepository()
    mine = await _add(changes, "1" * 40, at=T0)
    other = await _add(changes, "2" * 40, at=T0)
    await _persist(reviews, _review(mine, "b", score=7, ms=10, fail=False), PROJECT)
    await _persist(reviews, _review(mine, "a", score=None, ms=None, fail=True), PROJECT)
    await _persist(reviews, _review(other, "a", score=1, ms=1, fail=False), PROJECT)

    detail = await get_change_detail(changes, reviews, mine.id)

    assert detail is not None and detail.change == mine
    assert [r.agent for r in detail.reviews] == ["a", "b"]
    assert all(r.change_id == mine.id for r in detail.reviews)


async def test_change_detail_of_an_unknown_change_is_none() -> None:
    assert await get_change_detail(FakeChangeRepository(), FakeReviewRepository(), uuid4()) is None


async def test_agent_stats_delegates_to_the_repository() -> None:
    changes, reviews = FakeChangeRepository(), FakeReviewRepository()
    change = await _add(changes, "1" * 40, at=T0)
    await _persist(reviews, _review(change, "a", score=8, ms=100, fail=False), PROJECT)

    stats = await agent_stats(reviews)

    assert [(s.agent, s.total, s.avg_score, s.avg_duration_ms) for s in stats] == [
        ("a", 1, 8.0, 100.0)
    ]
