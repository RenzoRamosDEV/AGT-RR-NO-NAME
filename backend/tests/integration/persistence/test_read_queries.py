"""Consultas de lectura contra Postgres real: canal paginado, detalle y métricas por agente."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.project_repository import SqlAlchemyProjectRepository
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application.queries import list_changes
from duelo.application.read_models import ChangeCursor
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.review import Finding, Review, ReviewResult
from tests.integration.conftest import create_project

T0 = datetime(2026, 1, 1, tzinfo=UTC)
NO_FILTER = {"status": None, "q": None, "expected_agents": 2}


async def _add_change(
    session_factory: async_sessionmaker,
    project_id: UUID,
    i: int,
    *,
    at: datetime,
    kind: ChangeKind = ChangeKind.COMMIT,
    diff: str = "diff --git a/x b/x",
) -> Change:
    change = Change.new(
        project_id=project_id,
        kind=kind,
        ref="refs/heads/main",
        head_sha=f"{i:040d}",
        title=f"change {i}",
        author="renzo",
        url="https://example.com",
        diff=diff,
        diff_truncated=False,
        created_at=at,
    )
    event_ = ChangeCreated(
        change_id=change.id, project_id=project_id, kind=kind.value, head_sha=change.head_sha
    )
    async with session_factory() as session:
        return await SqlAlchemyChangeRepository(session).add(change, event_)


async def _page(
    session_factory: async_sessionmaker,
    project_id: UUID,
    *,
    limit: int,
    kind: ChangeKind | None = None,
    after: ChangeCursor | None = None,
):
    async with session_factory() as session:
        return await SqlAlchemyChangeRepository(session).list_for_project(
            project_id, kind=kind, limit=limit, after=after, **NO_FILTER
        )


# --- Proyectos -------------------------------------------------------------------------


async def test_list_all_returns_every_project_sorted_by_slug(
    session_factory: async_sessionmaker,
) -> None:
    ids = [await create_project(session_factory) for _ in range(3)]

    projects = await SqlAlchemyProjectRepository(session_factory).list_all()

    slugs = [p.slug for p in projects]
    assert slugs == sorted(slugs)
    assert {f"test-{i}" for i in ids} <= set(slugs)


# --- Canal -----------------------------------------------------------------------------


async def test_channel_is_newest_first_and_only_has_this_projects_changes(
    session_factory: async_sessionmaker,
) -> None:
    mine, other = await create_project(session_factory), await create_project(session_factory)
    oldest = await _add_change(session_factory, mine, 1, at=T0)
    newest = await _add_change(session_factory, mine, 2, at=T0 + timedelta(hours=1))
    await _add_change(session_factory, other, 3, at=T0 + timedelta(hours=2))

    rows = await _page(session_factory, mine, limit=10)

    assert [r.id for r in rows] == [newest.id, oldest.id]
    assert rows[0].title == "change 2" and rows[0].created_at == newest.created_at


async def test_channel_filters_by_kind(session_factory: async_sessionmaker) -> None:
    project = await create_project(session_factory)
    await _add_change(session_factory, project, 1, at=T0, kind=ChangeKind.COMMIT)
    pr = await _add_change(session_factory, project, 2, at=T0, kind=ChangeKind.PR)

    rows = await _page(session_factory, project, kind=ChangeKind.PR, limit=10)

    assert [(r.id, r.kind) for r in rows] == [(pr.id, ChangeKind.PR)]


async def test_keyset_pagination_neither_repeats_nor_skips_changes_with_equal_timestamps(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    # 7 changes en 3 instantes: hay empates que solo el `id` desempata.
    for i in range(7):
        await _add_change(session_factory, project, i, at=T0 + timedelta(minutes=i // 3))
    projects = SqlAlchemyProjectRepository(session_factory)
    slug = f"test-{project}"

    seen: list[UUID] = []
    after: ChangeCursor | None = None
    sizes: list[int] = []
    while True:
        async with session_factory() as session:
            page = await list_changes(
                projects,
                SqlAlchemyChangeRepository(session),
                slug=slug,
                kind=None,
                limit=3,
                after=after,
                **NO_FILTER,
                now=datetime.now(UTC),
                stale_after=timedelta(hours=1),
            )
        seen += [c.id for c in page.items]
        sizes.append(len(page.items))
        if page.next_cursor is None:
            break
        after = page.next_cursor

    everything = await _page(session_factory, project, limit=100)
    assert seen == [c.id for c in everything] and len(set(seen)) == 7
    assert sizes == [3, 3, 1]
    keys = [(c.created_at, c.id) for c in everything]
    assert keys == sorted(keys, reverse=True)


async def test_the_channel_query_never_loads_the_diff(
    session_factory: async_sessionmaker, engine: AsyncEngine
) -> None:
    project = await create_project(session_factory)
    await _add_change(session_factory, project, 1, at=T0, diff="SECRET-DIFF " * 1000)
    statements: list[str] = []

    def capture(conn, cursor, statement, *args):  # type: ignore[no-untyped-def]
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        async with session_factory() as session:
            await SqlAlchemyChangeRepository(session).list_for_project(
                project, kind=None, limit=10, after=None, **NO_FILTER
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)

    (select_sql,) = (s for s in statements if "FROM changes" in s)
    assert "changes.diff " not in select_sql and "changes.diff," not in select_sql
    assert "changes.diff_truncated" in select_sql


# --- Detalle ---------------------------------------------------------------------------


async def _persist_review(
    session_factory: async_sessionmaker, change: Change, review: Review
) -> None:
    ids = {"review_id": review.id, "change_id": change.id, "project_id": change.project_id}
    event_ = (
        ReviewFailed(agent=review.agent, error=review.error, **ids)
        if review.error
        else ReviewCompleted(agent=review.agent, **ids)
    )
    async with session_factory() as session:
        await SqlAlchemyReviewRepository(session).add(review, event_)


def _ok(change: Change, agent: str, *, score: int | None, ms: int, at: datetime) -> Review:
    return Review.succeeded(
        change_id=change.id,
        agent=agent,
        run=1,
        result=ReviewResult(
            summary="ok",
            score=score,
            findings=(Finding(severity="low", file="a.py", line=3, message="nit"),),
        ),
        raw_output="crudo",
        duration_ms=ms,
        created_at=at,
    )


def _ko(change: Change, agent: str, *, ms: int | None, at: datetime) -> Review:
    return Review.failed(
        change_id=change.id, agent=agent, run=1, error="boom", duration_ms=ms, created_at=at
    )


async def test_list_for_change_returns_completed_and_failed_in_creation_order(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    change = await _add_change(session_factory, project, 1, at=T0)
    other = await _add_change(session_factory, project, 2, at=T0)
    late = _ok(change, "agent_b", score=5, ms=1, at=T0 + timedelta(minutes=2))
    early = _ko(change, "agent_a", ms=None, at=T0 + timedelta(minutes=1))
    await _persist_review(session_factory, change, late)
    await _persist_review(session_factory, change, early)
    await _persist_review(session_factory, other, _ok(other, "agent_a", score=1, ms=1, at=T0))

    async with session_factory() as session:
        rows = await SqlAlchemyReviewRepository(session).list_for_change(change.id)

    assert [r.agent for r in rows] == ["agent_a", "agent_b"]
    assert rows[0].error == "boom" and rows[0].summary is None
    assert rows[1].findings == (Finding(severity="low", file="a.py", line=3, message="nit"),)


async def test_list_for_change_of_a_change_without_reviews_is_empty(
    session_factory: async_sessionmaker,
) -> None:
    async with session_factory() as session:
        assert await SqlAlchemyReviewRepository(session).list_for_change(uuid4()) == []


async def test_the_channel_brings_light_reviews_of_the_current_run_in_one_extra_query(
    session_factory: async_sessionmaker, engine: AsyncEngine
) -> None:
    project = await create_project(session_factory)
    changes = [await _add_change(session_factory, project, i, at=T0) for i in range(1, 6)]
    for change in changes:
        await _persist_review(session_factory, change, _ok(change, "agent_b", score=9, ms=5, at=T0))
        await _persist_review(session_factory, change, _ko(change, "agent_a", ms=7, at=T0))
    # Un reintento: el run 2 de `retried` no tiene reviews aún, y las del run 1 no deben salir.
    retried = changes[0]
    async with session_factory() as session:
        await SqlAlchemyChangeRepository(session).advance_run(retried.id, from_run=1, started_at=T0)
    statements: list[str] = []

    def capture(conn, cursor, statement, *args):  # type: ignore[no-untyped-def]
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        async with session_factory() as session:
            rows = await SqlAlchemyChangeRepository(session).list_for_project(
                project, kind=None, limit=10, after=None, **NO_FILTER
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)

    by_id = {row.id: row for row in rows}
    assert by_id[retried.id].reviews == ()
    for change in changes[1:]:
        briefs = by_id[change.id].reviews
        assert [(b.agent, b.status.value, b.score, b.duration_ms, b.run) for b in briefs] == [
            ("agent_a", "failed", None, 7, 1),
            ("agent_b", "completed", 9, 5, 1),
        ]
    # Sin N+1: dos consultas con 5 changes (canal + reviews de toda la página)...
    assert len(statements) == 2
    # ...y la segunda no toca las columnas pesadas.
    reviews_sql = statements[1]
    assert "FROM reviews" in reviews_sql
    for heavy in ("reviews.summary", "reviews.findings", "reviews.raw_output", "reviews.error"):
        assert heavy not in reviews_sql


# --- Estadísticas ----------------------------------------------------------------------


async def test_agent_stats_average_only_the_values_that_exist(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    tag = uuid4().hex[:12]
    good, flaky, broken = f"good-{tag}", f"flaky-{tag}", f"broken-{tag}"
    changes = [await _add_change(session_factory, project, i, at=T0) for i in range(3)]
    for change, (score, ms) in zip(changes[:2], [(8, 100), (6, 300)], strict=True):
        await _persist_review(session_factory, change, _ok(change, good, score=score, ms=ms, at=T0))
    await _persist_review(
        session_factory, changes[0], _ok(changes[0], flaky, score=None, ms=50, at=T0)
    )
    await _persist_review(session_factory, changes[1], _ko(changes[1], flaky, ms=None, at=T0))
    await _persist_review(session_factory, changes[0], _ko(changes[0], broken, ms=None, at=T0))
    await _persist_review(session_factory, changes[1], _ko(changes[1], broken, ms=None, at=T0))

    async with session_factory() as session:
        repo = SqlAlchemyReviewRepository(session)
        stats = {s.agent: s for s in await repo.agent_stats(project_id=None)}

    assert (stats[good].total, stats[good].completed, stats[good].failed) == (2, 2, 0)
    assert (stats[good].avg_score, stats[good].avg_duration_ms) == (7.0, 200.0)
    # Un score nulo o una duración nula no cuentan como 0 en la media.
    assert (stats[flaky].total, stats[flaky].completed, stats[flaky].failed) == (2, 1, 1)
    assert (stats[flaky].avg_score, stats[flaky].avg_duration_ms) == (None, 50.0)
    # Solo fallos sin score ni duración: medias nulas.
    assert (stats[broken].total, stats[broken].failed) == (2, 2)
    assert (stats[broken].avg_score, stats[broken].avg_duration_ms) == (None, None)
    assert list(stats) == sorted(stats)
