"""Consultas, round-trip de reviews, orden del outbox y rollback transaccional (Postgres real)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.models import EventModel, ReviewModel
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.application.ingest_change import ingest_change
from duelo.application.record_review import record_review_failure, record_review_success
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ReviewCompleted
from duelo.domain.review import Finding, Review, ReviewResult
from tests.integration.conftest import create_project

FINDINGS = (
    Finding("bug", "src/a.py", 10, "variable sin inicializar"),
    Finding("nit", "src/b.py", 3, "ñandú 🚀 comillas \" y ' y \\ barra"),
)


async def _ingest(session_factory: async_sessionmaker, head_sha: str = "a" * 40) -> Change:
    project_id = await create_project(session_factory)
    async with session_factory() as session:
        return await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=project_id,
            kind=ChangeKind.COMMIT,
            ref="refs/heads/main",
            head_sha=head_sha,
            title="fix: algo",
            author="renzo",
            url="https://example.com/c",
            diff="diff --git a/x b/x",
            diff_truncated=False,
        )


async def _record_ok(session_factory: async_sessionmaker, change: Change, agent: str) -> Review:
    async with session_factory() as session:
        return await record_review_success(
            SqlAlchemyReviewRepository(session),
            change=change,
            agent=agent,
            run=1,
            result=ReviewResult("todo bien", 8, FINDINGS),
            raw_output='{"ok": true}',
            duration_ms=250,
        )


# --- Consultas -----------------------------------------------------------------------


async def test_get_returns_the_stored_change_with_every_field(
    session_factory: async_sessionmaker,
) -> None:
    change = await _ingest(session_factory)

    async with session_factory() as session:
        stored = await SqlAlchemyChangeRepository(session).get(change.id)

    assert stored == change


async def test_get_returns_none_for_an_unknown_id(session_factory: async_sessionmaker) -> None:
    async with session_factory() as session:
        assert await SqlAlchemyChangeRepository(session).get(uuid4()) is None


async def test_reingesting_returns_the_same_change_that_get_returns(
    session_factory: async_sessionmaker,
) -> None:
    first = await _ingest(session_factory)
    async with session_factory() as session:
        again = await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=first.project_id,
            kind=first.kind,
            ref=first.ref,
            head_sha=first.head_sha,
            title="otro titulo",
            author="otra persona",
            url=first.url,
            diff="otro diff",
            diff_truncated=False,
        )

    assert again == first  # gana lo ya persistido, no lo reenviado


async def test_a_review_with_findings_roundtrips_through_jsonb_on_the_conflict_path(
    session_factory: async_sessionmaker,
) -> None:
    change = await _ingest(session_factory)
    original = await _record_ok(session_factory, change, "agent_1")

    again = await _record_ok(session_factory, change, "agent_1")  # camino ON CONFLICT -> SELECT

    assert again.id == original.id
    assert again.findings == FINDINGS
    assert (again.summary, again.score, again.raw_output, again.duration_ms) == (
        "todo bien",
        8,
        '{"ok": true}',
        250,
    )
    assert again.created_at.tzinfo is not None


# --- Outbox --------------------------------------------------------------------------


async def test_events_of_a_project_come_out_in_causal_order_with_increasing_ids(
    session_factory: async_sessionmaker,
) -> None:
    change = await _ingest(session_factory)
    await _record_ok(session_factory, change, "agent_1")
    async with session_factory() as session:
        await record_review_failure(
            SqlAlchemyReviewRepository(session),
            change=change,
            agent="agent_2",
            run=1,
            error="boom",
        )

    async with session_factory() as session:
        events = (
            (
                await session.execute(
                    select(EventModel)
                    .where(EventModel.project_id == change.project_id)
                    .order_by(EventModel.id)
                )
            )
            .scalars()
            .all()
        )

    assert [e.type for e in events] == ["change.created", "review.completed", "review.failed"]
    assert [e.id for e in events] == sorted({e.id for e in events})
    assert events[0].payload["change_id"] == str(change.id)


# --- Transacciones y rollback ----------------------------------------------------------


async def test_a_review_is_rolled_back_when_its_event_cannot_be_written(
    session_factory: async_sessionmaker,
) -> None:
    change = await _ingest(session_factory)
    review = Review.succeeded(
        change_id=change.id,
        agent="agent_1",
        run=1,
        result=ReviewResult("ok", 5, ()),
        raw_output=None,
        duration_ms=1,
        created_at=datetime.now(UTC),
    )
    broken_event = ReviewCompleted(review.id, change.id, uuid4(), "agent_1")  # proyecto inexistente

    async with session_factory() as session:
        with pytest.raises(Exception, match="(?i)foreign key"):
            await SqlAlchemyReviewRepository(session).add(review, broken_event)

    async with session_factory() as session:
        persisted = (
            await session.execute(select(ReviewModel).where(ReviewModel.id == review.id))
        ).scalar_one_or_none()
    assert persisted is None
