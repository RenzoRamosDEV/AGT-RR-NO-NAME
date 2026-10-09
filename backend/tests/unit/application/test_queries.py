import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from duelo.application.ingest_commit import ProjectNotFound
from duelo.application.queries import (
    agent_stats,
    change_events,
    get_change_detail,
    list_changes,
    list_projects,
    review_raw_output,
)
from duelo.application.read_models import ChangeCursor
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.project import Project
from duelo.domain.review import Finding, Review, ReviewResult
from duelo.domain.review_status import ChangeReviewStatus
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.event_log import FakeChangeEventRepository, FakeEventLog
from tests.fakes.project_repository import FakeProjectRepository
from tests.fakes.review_repository import FakeReviewRepository

PROJECT = Project(id=uuid4(), slug="acme/widgets")
T0 = datetime(2026, 1, 1, tzinfo=UTC)
_NO_FILTER = {"status": None, "q": None, "expected_agents": 2}


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
            projects, changes, slug=PROJECT.slug, kind=kind, limit=limit, after=after, **_NO_FILTER
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
        everything = await changes.list_for_project(
            PROJECT.id, kind=None, limit=1000, after=None, **_NO_FILTER
        )
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

    page = await list_changes(
        projects, changes, slug=PROJECT.slug, kind=None, limit=2, after=None, **_NO_FILTER
    )

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
            **_NO_FILTER,
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

    detail = await get_change_detail(changes, reviews, mine.id, expected_agents=2)

    assert detail is not None and detail.change == mine
    assert [r.agent for r in detail.reviews] == ["a", "b"]
    assert all(r.change_id == mine.id for r in detail.reviews)


async def test_change_detail_of_an_unknown_change_is_none() -> None:
    assert (
        await get_change_detail(
            FakeChangeRepository(), FakeReviewRepository(), uuid4(), expected_agents=2
        )
        is None
    )


async def test_agent_stats_delegates_to_the_repository() -> None:
    changes, reviews = FakeChangeRepository(), FakeReviewRepository()
    change = await _add(changes, "1" * 40, at=T0)
    await _persist(reviews, _review(change, "a", score=8, ms=100, fail=False), PROJECT)

    stats = await agent_stats(FakeProjectRepository(PROJECT), reviews, project=None)

    assert [(s.agent, s.total, s.avg_score, s.avg_duration_ms) for s in stats] == [
        ("a", 1, 8.0, 100.0)
    ]


async def _persist_review(
    reviews: FakeReviewRepository,
    change: Change,
    agent: str,
    *,
    fail: bool,
    run: int = 1,
    severities: tuple[str, ...] = (),
) -> None:
    ids = {"change_id": change.id, "agent": agent, "run": run, "created_at": T0}
    if fail:
        review = Review.failed(error="boom", duration_ms=None, **ids)
    else:
        findings = tuple(Finding(severity=s, file="f.py", line=1, message="m") for s in severities)
        review = Review.succeeded(
            result=ReviewResult(summary="ok", score=5, findings=findings),
            raw_output="RAW",
            duration_ms=1,
            **ids,
        )
    await _persist(reviews, review, PROJECT)


async def test_the_channel_filters_by_review_status_and_exposes_it() -> None:
    reviews = FakeReviewRepository()
    projects, changes = FakeProjectRepository(PROJECT), FakeChangeRepository(reviews)
    done = await _add(changes, "1" * 40, at=T0)
    broken = await _add(changes, "2" * 40, at=T0 + timedelta(minutes=1))
    fresh = await _add(changes, "3" * 40, at=T0 + timedelta(minutes=2))
    for agent in ("a", "b"):
        await _persist_review(reviews, done, agent, fail=False)
        await _persist_review(reviews, broken, agent, fail=True)

    async def listed(status: set[ChangeReviewStatus] | None) -> dict[UUID, ChangeReviewStatus]:
        page = await list_changes(
            projects,
            changes,
            slug=PROJECT.slug,
            kind=None,
            status=frozenset(status) if status else None,
            q=None,
            expected_agents=2,
            limit=10,
            after=None,
        )
        return {c.id: c.review_status for c in page.items}

    assert await listed(None) == {
        fresh.id: ChangeReviewStatus.PENDING,
        broken.id: ChangeReviewStatus.FAILED,
        done.id: ChangeReviewStatus.COMPLETED,
    }
    assert set(await listed({ChangeReviewStatus.FAILED})) == {broken.id}
    in_progress = {ChangeReviewStatus.PENDING, ChangeReviewStatus.RUNNING}
    assert set(await listed(in_progress)) == {fresh.id}


async def test_pagination_applies_the_filter_before_the_limit() -> None:
    reviews = FakeReviewRepository()
    projects, changes = FakeProjectRepository(PROJECT), FakeChangeRepository(reviews)
    failing: list[UUID] = []
    for i in range(6):
        change = await _add(changes, f"{i:040d}", at=T0 + timedelta(minutes=i))
        if i % 2 == 0:
            failing.append(change.id)
            for agent in ("a", "b"):
                await _persist_review(reviews, change, agent, fail=True)

    pages: list[list[UUID]] = []
    after: ChangeCursor | None = None
    while True:
        page = await list_changes(
            projects,
            changes,
            slug=PROJECT.slug,
            kind=None,
            status=frozenset({ChangeReviewStatus.FAILED}),
            q=None,
            expected_agents=2,
            limit=2,
            after=after,
        )
        pages.append([c.id for c in page.items])
        if page.next_cursor is None:
            break
        after = page.next_cursor

    assert pages == [[failing[2], failing[1]], [failing[0]]]


async def test_detail_reports_status_and_findings_of_the_current_run_only() -> None:
    changes, reviews = FakeChangeRepository(), FakeReviewRepository()
    change = await _add(changes, "1" * 40, at=T0)
    await _persist_review(reviews, change, "a", fail=False, severities=("bug", "bug"))  # run 1
    await _persist_review(reviews, change, "b", fail=True)  # run 1
    change = await changes.advance_run(change.id, from_run=1)  # type: ignore[assignment]
    await _persist_review(reviews, change, "a", fail=False, run=2, severities=("Risk", "banana"))
    await _persist_review(reviews, change, "b", fail=True, run=2)

    detail = await get_change_detail(changes, reviews, change.id, expected_agents=2)

    assert detail is not None
    assert detail.review_status is ChangeReviewStatus.PARTIAL_FAILED
    summary = detail.findings_summary
    assert (summary.total, summary.bug, summary.risk, summary.other) == (2, 0, 1, 1)
    assert len(detail.reviews) == 4  # el historial completo sigue visible


async def test_detail_of_a_change_without_reviews_is_pending_with_no_findings() -> None:
    changes, reviews = FakeChangeRepository(), FakeReviewRepository()
    change = await _add(changes, "1" * 40, at=T0)

    detail = await get_change_detail(changes, reviews, change.id, expected_agents=2)

    assert detail is not None and detail.review_status is ChangeReviewStatus.PENDING
    assert detail.findings_summary.total == 0


async def test_the_search_text_and_one_extra_row_are_requested_from_the_repository() -> None:
    class Spy(FakeChangeRepository):
        calls: list[dict[str, object]] = []

        async def list_for_project(self, project_id: UUID, **kwargs):  # type: ignore[no-untyped-def]
            self.calls.append(kwargs)
            return await super().list_for_project(project_id, **kwargs)

    changes = Spy()
    await _add(changes, "1" * 40, at=T0)
    await _add(changes, "2" * 40, at=T0 + timedelta(minutes=1))
    only = frozenset({ChangeReviewStatus.PENDING})

    page = await list_changes(
        FakeProjectRepository(PROJECT),
        changes,
        slug=PROJECT.slug,
        kind=None,
        status=only,
        q="change 1",
        expected_agents=3,
        limit=1,
        after=None,
    )

    (call,) = changes.calls
    assert call["q"] == "change 1" and call["status"] == only and call["expected_agents"] == 3
    assert call["limit"] == 2  # uno de más para saber si hay página siguiente
    assert [c.head_sha for c in page.items] == ["1" * 40]


async def test_agent_stats_can_be_scoped_to_a_project() -> None:
    other_project = Project(id=uuid4(), slug="otro/repo")
    projects = FakeProjectRepository(PROJECT, other_project)
    reviews = FakeReviewRepository()
    changes = FakeChangeRepository(reviews)
    mine = await _add(changes, "1" * 40, at=T0)
    theirs = await _add(changes, "2" * 40, at=T0, project=other_project)
    await _persist(reviews, _review(mine, "a", score=8, ms=100, fail=False), PROJECT)
    await _persist(reviews, _review(theirs, "a", score=2, ms=900, fail=False), other_project)

    scoped = await agent_stats(projects, reviews, project=PROJECT.slug)
    everyone = await agent_stats(projects, reviews, project=None)

    assert [(s.total, s.avg_score) for s in scoped] == [(1, 8.0)]
    assert [(s.total, s.avg_score) for s in everyone] == [(2, 5.0)]


async def test_agent_stats_of_a_project_without_reviews_is_empty_not_an_error() -> None:
    projects, reviews = FakeProjectRepository(PROJECT), FakeReviewRepository()

    assert await agent_stats(projects, reviews, project=PROJECT.slug) == []


async def test_agent_stats_of_an_unknown_project_raises() -> None:
    with pytest.raises(ProjectNotFound) as error:
        await agent_stats(FakeProjectRepository(PROJECT), FakeReviewRepository(), project="no/hay")

    assert error.value.slug == "no/hay"


async def _history() -> tuple[FakeChangeRepository, FakeEventLog, Change]:
    log = FakeEventLog()
    reviews = FakeReviewRepository(log)
    changes = FakeChangeRepository(reviews, log)
    change = await _add(changes, "1" * 40, at=T0)
    await _persist(reviews, _review(change, "a", score=5, ms=10, fail=False), PROJECT)
    await _persist(reviews, _review(change, "b", score=None, ms=None, fail=True), PROJECT)
    return changes, log, change


async def test_change_events_are_ordered_and_expose_only_agent_and_review_id() -> None:
    changes, log, change = await _history()

    events = await change_events(changes, FakeChangeEventRepository(log), change.id)

    assert events is not None
    assert [(e.type, e.agent) for e in events] == [
        ("change.created", None),
        ("review.completed", "a"),
        ("review.failed", "b"),
    ]
    assert [e.id for e in events] == sorted(e.id for e in events)
    assert events[0].review_id is None and events[1].review_id is not None
    assert all(isinstance(e.created_at, datetime) for e in events)


async def test_change_events_never_expose_the_error_text_or_other_payload_fields() -> None:
    changes, log, change = await _history()
    log.append_raw(
        project_id=PROJECT.id,
        type="review.failed",
        payload={
            "change_id": str(change.id),
            "agent": "c",
            "error": "Traceback: token=SECRETO",
            "raw_output": "SALIDA CRUDA",
        },
    )

    events = await change_events(changes, FakeChangeEventRepository(log), change.id)

    assert events is not None
    assert "SECRETO" not in repr(events) and "SALIDA CRUDA" not in repr(events)
    assert not hasattr(events[-1], "error") and not hasattr(events[-1], "payload")


async def test_change_events_skip_unknown_types_and_other_changes() -> None:
    changes, log, change = await _history()
    other = await _add(changes, "2" * 40, at=T0)
    log.append_raw(project_id=PROJECT.id, type="vote.cast", payload={"change_id": str(change.id)})
    log.append_raw(
        project_id=PROJECT.id,
        type="review.completed",
        payload={"change_id": str(other.id), "agent": "z"},
    )

    events = await change_events(changes, FakeChangeEventRepository(log), change.id)

    assert events is not None
    assert [e.type for e in events] == ["change.created", "review.completed", "review.failed"]
    assert "z" not in [e.agent for e in events]


async def test_change_events_tolerate_a_malformed_review_id_and_a_non_text_agent() -> None:
    changes, log, change = await _history()
    log.append_raw(
        project_id=PROJECT.id,
        type="review.completed",
        payload={"change_id": str(change.id), "agent": 7, "review_id": "no-es-uuid"},
    )

    events = await change_events(changes, FakeChangeEventRepository(log), change.id)

    assert events is not None
    assert events[-1].agent is None and events[-1].review_id is None


async def test_change_events_of_an_unknown_change_is_none() -> None:
    log = FakeEventLog()

    assert (
        await change_events(FakeChangeRepository(), FakeChangeEventRepository(log), uuid4()) is None
    )


async def test_review_raw_output_returns_it_only_when_the_review_has_one() -> None:
    changes, reviews = FakeChangeRepository(), FakeReviewRepository()
    change = await _add(changes, "1" * 40, at=T0)
    done = Review.succeeded(
        change_id=change.id,
        agent="a",
        run=1,
        result=ReviewResult(summary="ok", score=1),
        raw_output="SALIDA",
        duration_ms=1,
        created_at=T0,
    )
    quiet = _review(change, "b", score=1, ms=1, fail=False)  # raw_output=None
    broken = _review(change, "c", score=None, ms=None, fail=True)
    for review in (done, quiet, broken):
        await _persist(reviews, review, PROJECT)

    output = await review_raw_output(reviews, done.id)

    assert output is not None and (output.review_id, output.raw_output) == (done.id, "SALIDA")
    assert await review_raw_output(reviews, quiet.id) is None
    assert await review_raw_output(reviews, broken.id) is None
    assert await review_raw_output(reviews, uuid4()) is None
