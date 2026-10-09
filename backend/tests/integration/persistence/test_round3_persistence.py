"""Ronda 3 contra Postgres real: resumen del diff, stats por proyecto, review por id y eventos."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.event_repository import SqlAlchemyChangeEventRepository
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application.queries import change_events
from duelo.domain.change import Change, ChangeKind
from duelo.domain.diff import summarize_diff
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.review import Review, ReviewResult
from tests.integration.conftest import create_project

T0 = datetime(2026, 1, 1, tzinfo=UTC)
DIFF = (
    "diff --git a/a.py b/a.py\n@@ -1 +1,2 @@\n-x\n+y\n+z\ndiff --git a/b b/b\n@@ -1 +0,0 @@\n-q\n"
)


async def _add(session_factory: async_sessionmaker, project: UUID, i: int, diff: str) -> Change:
    change = Change.new(
        project_id=project,
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha=f"{i:040d}",
        title=f"change {i}",
        author="renzo",
        url="https://example.com",
        diff=diff,
        diff_truncated=False,
        created_at=T0,
    )
    event = ChangeCreated(
        change_id=change.id, project_id=project, kind="commit", head_sha=change.head_sha
    )
    async with session_factory() as session:
        return await SqlAlchemyChangeRepository(session).add(change, event)


async def _review(
    session_factory: async_sessionmaker,
    change: Change,
    agent: str,
    *,
    fail: bool = False,
    raw: str | None = "crudo",
) -> Review:
    ids = {"change_id": change.id, "project_id": change.project_id, "agent": agent}
    if fail:
        review = Review.failed(
            change_id=change.id,
            agent=agent,
            run=1,
            error="Traceback: token=SECRETO",
            duration_ms=None,
            created_at=T0,
        )
        event: ReviewCompleted | ReviewFailed = ReviewFailed(
            review_id=review.id, error="Traceback: token=SECRETO", **ids
        )
    else:
        review = Review.succeeded(
            change_id=change.id,
            agent=agent,
            run=1,
            result=ReviewResult(summary="ok", score=6),
            raw_output=raw,
            duration_ms=40,
            created_at=T0,
        )
        event = ReviewCompleted(review_id=review.id, **ids)
    async with session_factory() as session:
        return await SqlAlchemyReviewRepository(session).add(review, event)


# --- diff_summary ----------------------------------------------------------------------------


async def test_the_diff_summary_is_stored_and_read_back_by_get_and_by_the_channel(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    change = await _add(session_factory, project, 1, DIFF)

    async with session_factory() as session:
        repo = SqlAlchemyChangeRepository(session)
        loaded = await repo.get(change.id)
        (listed,) = await repo.list_for_project(
            project, kind=None, status=None, q=None, expected_agents=2, limit=10, after=None
        )

    expected = summarize_diff(DIFF)
    assert expected.files_changed == 2 and expected.additions == 2 and expected.deletions == 2
    assert loaded is not None and loaded.diff_summary == expected
    assert listed.diff_summary == expected


async def test_a_nul_in_a_file_path_is_sanitized_instead_of_failing_the_insert(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    diff = "diff --git a/a\x00b b/a\x00b\n@@ -1 +1 @@\n-x\n+y\n"

    change = await _add(session_factory, project, 1, diff)

    async with session_factory() as session:
        loaded = await SqlAlchemyChangeRepository(session).get(change.id)
    assert loaded is not None and loaded.diff_summary.files[0].path == "a�b"


# --- Reviews y estadísticas por proyecto ------------------------------------------------------


async def test_a_review_is_found_by_id_with_its_raw_output(
    session_factory: async_sessionmaker,
) -> None:
    change = await _add(session_factory, await create_project(session_factory), 1, DIFF)
    done = await _review(session_factory, change, "a", raw="SALIDA")
    broken = await _review(session_factory, change, "b", fail=True)

    async with session_factory() as session:
        repo = SqlAlchemyReviewRepository(session)
        found = await repo.get(done.id)
        failed = await repo.get(broken.id)
        missing = await repo.get(uuid4())

    assert found is not None and found.raw_output == "SALIDA"
    assert failed is not None and failed.raw_output is None
    assert missing is None


async def test_agent_stats_can_be_scoped_to_one_project(
    session_factory: async_sessionmaker,
) -> None:
    mine, other = await create_project(session_factory), await create_project(session_factory)
    agent = f"agent-{uuid4().hex[:10]}"
    mine_change = await _add(session_factory, mine, 1, DIFF)
    other_change = await _add(session_factory, other, 2, DIFF)
    await _review(session_factory, mine_change, agent)
    await _review(session_factory, other_change, agent, fail=True)
    await _review(session_factory, other_change, f"{agent}-2")

    async with session_factory() as session:
        repo = SqlAlchemyReviewRepository(session)
        scoped = {s.agent: s for s in await repo.agent_stats(project_id=mine)}
        elsewhere = {s.agent: s for s in await repo.agent_stats(project_id=other)}
        everywhere = {s.agent: s for s in await repo.agent_stats(project_id=None)}
        nobody = await repo.agent_stats(project_id=await create_project(session_factory))

    assert (scoped[agent].total, scoped[agent].completed, scoped[agent].failed) == (1, 1, 0)
    assert f"{agent}-2" not in scoped
    assert (elsewhere[agent].total, elsewhere[agent].failed) == (1, 1)
    assert everywhere[agent].total == 2
    assert nobody == []


# --- Eventos -----------------------------------------------------------------------------------


async def test_events_come_in_write_order_and_only_for_that_change(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    mine = await _add(session_factory, project, 1, DIFF)
    other = await _add(session_factory, project, 2, DIFF)
    done = await _review(session_factory, mine, "a")
    await _review(session_factory, other, "a")
    broken = await _review(session_factory, mine, "b", fail=True)

    async with session_factory() as session:
        events = await change_events(
            SqlAlchemyChangeRepository(session), SqlAlchemyChangeEventRepository(session), mine.id
        )

    assert events is not None
    assert [(e.type, e.agent, e.review_id) for e in events] == [
        ("change.created", None, None),
        ("review.completed", "a", done.id),
        ("review.failed", "b", broken.id),
    ]
    assert [e.id for e in events] == sorted(e.id for e in events)
    assert "SECRETO" not in repr(events)


async def test_raw_events_of_another_project_with_the_same_change_id_are_not_returned(
    session_factory: async_sessionmaker,
) -> None:
    project, elsewhere = (
        await create_project(session_factory),
        await create_project(session_factory),
    )
    change = await _add(session_factory, project, 1, DIFF)

    async with session_factory() as session:
        repo = SqlAlchemyChangeEventRepository(session)
        mine = await repo.list_for_change(project, change.id)
        theirs = await repo.list_for_change(elsewhere, change.id)

    assert [e.type for e in mine] == ["change.created"]
    assert theirs == []
