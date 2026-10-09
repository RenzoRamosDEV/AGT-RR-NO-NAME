"""Bordes contra Postgres real: límites, NUL y regresiones de lo que ya funcionaba."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from review_arena.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from review_arena.adapters.persistence.models import ReviewModel
from review_arena.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from review_arena.application.ingest_change import ingest_change
from review_arena.application.record_review import record_review_failure, record_review_success
from review_arena.domain.change import (
    MAX_AUTHOR,
    MAX_HEAD_SHA,
    MAX_REF,
    MAX_TITLE,
    MAX_URL,
    Change,
    ChangeKind,
)
from review_arena.domain.review import MAX_AGENT, Finding, ReviewResult
from tests.integration.conftest import create_project

NUL = "\x00"
FFFD = "�"


async def _ingest(session_factory: async_sessionmaker, **overrides: object) -> Change:
    project_id = await create_project(session_factory)
    fields: dict[str, object] = {
        "kind": ChangeKind.COMMIT,
        "ref": "refs/heads/main",
        "head_sha": "a" * 40,
        "title": "fix: algo",
        "author": "renzo",
        "url": "https://example.com/commit/a",
        "diff": "diff --git a/x b/x",
        "diff_truncated": False,
    }
    fields.update(overrides)
    async with session_factory() as session:
        return await ingest_change(
            SqlAlchemyChangeRepository(session),
            project_id=project_id,
            **fields,  # type: ignore[arg-type]
        )


async def _reload(session_factory: async_sessionmaker, change: Change) -> Change:
    async with session_factory() as session:
        stored = await SqlAlchemyChangeRepository(session).get(change.id)
    assert stored is not None
    return stored


async def test_every_field_at_its_maximum_length_roundtrips_intact(
    session_factory: async_sessionmaker,
) -> None:
    change = await _ingest(
        session_factory,
        head_sha="s" * MAX_HEAD_SHA,
        ref="r" * MAX_REF,
        url="u" * MAX_URL,
        title="t" * MAX_TITLE,
        author="a" * MAX_AUTHOR,
    )

    stored = await _reload(session_factory, change)

    assert stored.head_sha == "s" * MAX_HEAD_SHA
    assert stored.ref == "r" * MAX_REF
    assert stored.url == "u" * MAX_URL
    assert stored.title == "t" * MAX_TITLE
    assert stored.author == "a" * MAX_AUTHOR


async def test_overlong_title_and_author_are_stored_truncated_not_rejected(
    session_factory: async_sessionmaker,
) -> None:
    change = await _ingest(session_factory, title="t" * (MAX_TITLE + 100), author="a" * 999)

    stored = await _reload(session_factory, change)

    assert stored.title == "t" * MAX_TITLE
    assert stored.author == "a" * MAX_AUTHOR


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("head_sha", "b" * (MAX_HEAD_SHA + 1)),
        ("ref", "r" * (MAX_REF + 1)),
        ("url", "u" * (MAX_URL + 1)),
        ("head_sha", ""),
        ("ref", f"refs/{NUL}"),
    ],
)
async def test_invalid_identifiers_are_rejected_before_touching_the_database(
    session_factory: async_sessionmaker, field: str, value: str
) -> None:
    with pytest.raises(ValueError, match=field):
        await _ingest(session_factory, **{field: value})


async def test_nul_in_title_author_and_diff_is_stored_as_replacement_character(
    session_factory: async_sessionmaker,
) -> None:
    change = await _ingest(
        session_factory,
        title=f"ti{NUL}tle",
        author=f"au{NUL}thor",
        diff=f"line1{NUL}line2",
    )

    stored = await _reload(session_factory, change)

    assert stored.title == f"ti{FFFD}tle"
    assert stored.author == f"au{FFFD}thor"
    assert stored.diff == f"line1{FFFD}line2"


async def test_nul_in_review_text_and_jsonb_findings_is_stored_as_replacement_character(
    session_factory: async_sessionmaker,
) -> None:
    change = await _ingest(session_factory)
    result = ReviewResult(
        summary=f"sum{NUL}mary",
        score=4,
        findings=(Finding(f"se{NUL}v", f"fi{NUL}le.py", 7, f"me{NUL}ssage"),),
    )

    async with session_factory() as session:
        await record_review_success(
            SqlAlchemyReviewRepository(session),
            change=change,
            agent="agent_1",
            run=1,
            result=result,
            raw_output=f"raw{NUL}out",
            duration_ms=5,
        )
    async with session_factory() as session:
        await record_review_failure(
            SqlAlchemyReviewRepository(session),
            change=change,
            agent="agent_2",
            run=1,
            error=f"bo{NUL}om",
        )
        rows = {
            r.agent: r
            for r in (
                await session.execute(select(ReviewModel).where(ReviewModel.change_id == change.id))
            )
            .scalars()
            .all()
        }

    ok, failed = rows["agent_1"], rows["agent_2"]
    assert ok.summary == f"sum{FFFD}mary"
    assert ok.raw_output == f"raw{FFFD}out"
    assert ok.findings == [
        {"severity": f"se{FFFD}v", "file": f"fi{FFFD}le.py", "line": 7, "message": f"me{FFFD}ssage"}
    ]
    assert failed.error == f"bo{FFFD}om"


async def test_agent_name_at_the_limit_persists(session_factory: async_sessionmaker) -> None:
    change = await _ingest(session_factory)
    agent = "g" * MAX_AGENT

    async with session_factory() as session:
        review = await record_review_failure(
            SqlAlchemyReviewRepository(session), change=change, agent=agent, run=1, error="x"
        )

    assert review.agent == agent


# --- Regresiones: ya funcionaban en el sondeo y no deben romperse ---------------------


async def test_regression_five_megabyte_diff_is_persisted_and_read_back(
    session_factory: async_sessionmaker,
) -> None:
    diff = "x" * 5_000_000

    change = await _ingest(session_factory, diff=diff)

    assert (await _reload(session_factory, change)).diff == diff


async def test_regression_sql_metacharacters_are_stored_as_literal_text(
    session_factory: async_sessionmaker,
) -> None:
    hostile = "'; DROP TABLE changes; --"

    change = await _ingest(session_factory, title=hostile, author='" OR 1=1 --')

    stored = await _reload(session_factory, change)
    assert stored.title == hostile
    assert stored.author == '" OR 1=1 --'
    # la tabla sigue existiendo y la lectura funciona
    assert await _reload(session_factory, change) == stored


async def test_regression_unicode_and_emoji_roundtrip_intact(
    session_factory: async_sessionmaker,
) -> None:
    text = "fix: 🚀 ñandú 日本語 ‮ rtl"

    change = await _ingest(session_factory, title=text)

    assert (await _reload(session_factory, change)).title == text


async def test_uuid_ids_are_returned_as_uuid_objects(session_factory: async_sessionmaker) -> None:
    change = await _ingest(session_factory)

    stored = await _reload(session_factory, change)

    assert isinstance(stored.id, UUID)
    assert isinstance(stored.project_id, UUID)
