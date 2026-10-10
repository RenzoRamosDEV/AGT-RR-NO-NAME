"""Filtros por estado y texto del canal, y `advance_run`, contra Postgres real."""

from __future__ import annotations

import asyncio
import itertools
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application.read_models import ChangeCursor, ChangeSummary
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.review import Review, ReviewResult
from duelo.domain.review_status import ChangeReviewStatus, review_status_from_counts
from tests.integration.conftest import create_project

_RETRIED_AT = datetime(2026, 2, 1, tzinfo=UTC)

T0 = datetime(2026, 1, 1, tzinfo=UTC)


async def _add_change(
    session_factory: async_sessionmaker,
    project_id: UUID,
    i: int,
    *,
    title: str = "",
    author: str = "renzo",
    ref: str = "refs/heads/main",
) -> Change:
    change = Change.new(
        project_id=project_id,
        kind=ChangeKind.COMMIT,
        ref=ref,
        head_sha=f"{i:040d}",
        title=title or f"change {i}",
        author=author,
        url="https://example.com",
        diff="d",
        diff_truncated=False,
        created_at=T0 + timedelta(minutes=i),
    )
    event = ChangeCreated(
        change_id=change.id, project_id=project_id, kind="commit", head_sha=change.head_sha
    )
    async with session_factory() as session:
        return await SqlAlchemyChangeRepository(session).add(change, event)


async def _review(
    session_factory: async_sessionmaker, change: Change, agent: str, run: int, *, fail: bool
) -> None:
    ids = {"change_id": change.id, "agent": agent, "run": run, "created_at": T0}
    if fail:
        review = Review.failed(error="boom", duration_ms=None, **ids)
        event = ReviewFailed(
            review_id=review.id,
            change_id=change.id,
            project_id=change.project_id,
            agent=agent,
            error="boom",
        )
    else:
        review = Review.succeeded(
            result=ReviewResult(summary="ok", score=1), raw_output=None, duration_ms=1, **ids
        )
        event = ReviewCompleted(
            review_id=review.id, change_id=change.id, project_id=change.project_id, agent=agent
        )
    async with session_factory() as session:
        await SqlAlchemyReviewRepository(session).add(review, event)


async def _list(
    session_factory: async_sessionmaker,
    project_id: UUID,
    *,
    status: frozenset[ChangeReviewStatus] | None = None,
    q: str | None = None,
    expected_agents: int = 2,
    limit: int = 100,
    after: ChangeCursor | None = None,
) -> list[ChangeSummary]:
    async with session_factory() as session:
        return await SqlAlchemyChangeRepository(session).list_for_project(
            project_id,
            kind=None,
            status=status,
            q=q,
            expected_agents=expected_agents,
            limit=limit,
            after=after,
        )


@pytest.mark.parametrize("expected_agents", [1, 2, 3])
async def test_sql_filter_agrees_with_the_domain_status_for_every_counter_combination(
    session_factory: async_sessionmaker, expected_agents: int
) -> None:
    """El predicado SQL duplica `review_status_from_counts`: se recorre toda la matriz de
    contadores (hasta 3 completadas × 3 fallidas) para que no puedan divergir."""
    project = await create_project(session_factory)
    agents = ["a", "b", "c", "d", "e", "f"]
    expected_by_change: dict[UUID, ChangeReviewStatus] = {}
    for i, (completed, failed) in enumerate(itertools.product(range(4), range(4))):
        change = await _add_change(session_factory, project, i)
        for agent in agents[:completed]:
            await _review(session_factory, change, agent, 1, fail=False)
        for agent in agents[completed : completed + failed]:
            await _review(session_factory, change, agent, 1, fail=True)
        expected_by_change[change.id] = review_status_from_counts(
            completed=completed, failed=failed, expected_agents=expected_agents
        )

    everything = await _list(session_factory, project, expected_agents=expected_agents)
    assert {c.id: c.review_status for c in everything} == expected_by_change

    for status in ChangeReviewStatus:
        filtered = await _list(
            session_factory,
            project,
            status=frozenset({status}),
            expected_agents=expected_agents,
        )
        assert {c.id for c in filtered} == {
            cid for cid, st in expected_by_change.items() if st is status
        }, status


async def test_several_statuses_are_ored_and_paginate_with_the_cursor(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    wanted: list[UUID] = []
    for i in range(6):
        change = await _add_change(session_factory, project, i)
        if i % 3 == 0:  # fallida
            await _review(session_factory, change, "a", 1, fail=True)
            await _review(session_factory, change, "b", 1, fail=True)
            wanted.append(change.id)
        elif i % 3 == 1:  # pendiente
            wanted.append(change.id)
        else:  # completada: no se pide
            await _review(session_factory, change, "a", 1, fail=False)
            await _review(session_factory, change, "b", 1, fail=False)
    status = frozenset({ChangeReviewStatus.FAILED, ChangeReviewStatus.PENDING})

    seen: list[UUID] = []
    after: ChangeCursor | None = None
    while True:
        rows = await _list(session_factory, project, status=status, limit=2, after=after)
        seen += [r.id for r in rows]
        if len(rows) < 2:
            break
        after = ChangeCursor(created_at=rows[-1].created_at, id=rows[-1].id)

    assert seen == list(reversed(wanted))


async def test_only_the_current_run_counts_for_the_status(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    change = await _add_change(session_factory, project, 1)
    await _review(session_factory, change, "a", 1, fail=True)
    await _review(session_factory, change, "b", 1, fail=True)
    async with session_factory() as session:
        assert await SqlAlchemyChangeRepository(session).advance_run(
            change.id, from_run=1, started_at=_RETRIED_AT
        )

    (row,) = await _list(session_factory, project)
    assert (row.run, row.review_status) == (2, ChangeReviewStatus.PENDING)

    await _review(session_factory, change, "a", 2, fail=False)
    (row,) = await _list(session_factory, project)
    assert row.review_status is ChangeReviewStatus.RUNNING


async def test_search_matches_the_four_fields_ignoring_case(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    title = await _add_change(session_factory, project, 1, title="Arreglar el LOGIN")
    author = await _add_change(session_factory, project, 2, author="Maria")
    ref = await _add_change(session_factory, project, 3, ref="refs/heads/feature/pagos")
    sha = await _add_change(session_factory, project, 4)

    async def ids(q: str) -> list[UUID]:
        return [c.id for c in await _list(session_factory, project, q=q)]

    assert await ids("login") == [title.id]
    assert await ids("MARIA") == [author.id]
    assert await ids("FEATURE/pagos") == [ref.id]
    assert await ids(sha.head_sha[-6:]) == [sha.id]
    assert await ids("inexistente") == []


@pytest.mark.regression
async def test_like_wildcards_in_the_search_are_literal_text(
    session_factory: async_sessionmaker,
) -> None:
    """Sin escapar, `50%` coincidiría con '500 casos' y `_` con cualquier carácter."""
    project = await create_project(session_factory)
    literal = await _add_change(session_factory, project, 1, title="50% más rápido")
    await _add_change(session_factory, project, 2, title="500 casos")
    underscore = await _add_change(session_factory, project, 3, title="fix_login")
    await _add_change(session_factory, project, 4, title="fixXlogin")
    backslash = await _add_change(session_factory, project, 5, title=r"ruta C:\temp")

    async def ids(q: str) -> list[UUID]:
        return [c.id for c in await _list(session_factory, project, q=q)]

    assert await ids("50%") == [literal.id]
    assert await ids("fix_login") == [underscore.id]
    assert await ids("%") == [literal.id]
    assert await ids(r"C:\t") == [backslash.id]


async def test_status_and_search_combine(session_factory: async_sessionmaker) -> None:
    project = await create_project(session_factory)
    target = await _add_change(session_factory, project, 1, title="pagos roto")
    other = await _add_change(session_factory, project, 2, title="login roto")
    await _add_change(session_factory, project, 3, title="pagos nuevo")
    for change in (target, other):
        await _review(session_factory, change, "a", 1, fail=True)
        await _review(session_factory, change, "b", 1, fail=True)

    rows = await _list(
        session_factory, project, status=frozenset({ChangeReviewStatus.FAILED}), q="pagos"
    )

    assert [r.id for r in rows] == [target.id]


async def test_advance_run_is_a_compare_and_swap(session_factory: async_sessionmaker) -> None:
    project = await create_project(session_factory)
    change = await _add_change(session_factory, project, 1)

    async def advance(from_run: int) -> Change | None:
        async with session_factory() as session:
            return await SqlAlchemyChangeRepository(session).advance_run(
                change.id, from_run=from_run, started_at=_RETRIED_AT
            )

    stale = await advance(5)  # run actual 1: no coincide
    advanced = await advance(1)
    again = await advance(1)  # ya está en 2: el segundo intento pierde

    assert (stale, again) == (None, None)
    assert advanced is not None and advanced.run == 2 and advanced.id == change.id
    async with session_factory() as session:
        stored = await SqlAlchemyChangeRepository(session).get(change.id)
    assert stored is not None and stored.run == 2


async def test_concurrent_advance_run_has_exactly_one_winner(
    session_factory: async_sessionmaker,
) -> None:
    project = await create_project(session_factory)
    change = await _add_change(session_factory, project, 1)

    async def advance() -> Change | None:
        async with session_factory() as session:
            return await SqlAlchemyChangeRepository(session).advance_run(
                change.id, from_run=1, started_at=_RETRIED_AT
            )

    results = await asyncio.gather(*(advance() for _ in range(8)))

    assert sum(r is not None for r in results) == 1
    async with session_factory() as session:
        stored = await SqlAlchemyChangeRepository(session).get(change.id)
    assert stored is not None and stored.run == 2


async def test_advance_run_of_an_unknown_change_is_none(
    session_factory: async_sessionmaker,
) -> None:
    from uuid import uuid4

    async with session_factory() as session:
        result = await SqlAlchemyChangeRepository(session).advance_run(
            uuid4(), from_run=1, started_at=_RETRIED_AT
        )
        assert result is None
