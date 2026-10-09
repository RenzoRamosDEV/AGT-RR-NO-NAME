"""Ley de idempotencia: n ingestas con claves aleatorias dejan tantos registros como claves
distintas, y la misma clave devuelve siempre la misma entidad."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from hypothesis import given
from hypothesis import strategies as st

from review_arena.application.ingest_change import ingest_change
from review_arena.application.record_review import record_review_success
from review_arena.domain.change import Change, ChangeKind
from review_arena.domain.review import ReviewResult
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.review_repository import FakeReviewRepository

PROJECTS = [uuid4() for _ in range(3)]
SHAS = [f"{i:040d}" for i in range(4)]


@given(st.lists(st.tuples(st.integers(0, 2), st.integers(0, 3), st.sampled_from(ChangeKind))))
def test_ingesting_any_sequence_of_keys_creates_one_change_and_event_per_distinct_key(
    keys: list[tuple[int, int, ChangeKind]],
) -> None:
    async def scenario() -> tuple[FakeChangeRepository, dict[tuple, set[UUID]]]:
        repo = FakeChangeRepository()
        ids: dict[tuple, set[UUID]] = {}
        for project, sha, kind in keys:
            change = await ingest_change(
                repo,
                project_id=PROJECTS[project],
                kind=kind,
                ref="r",
                head_sha=SHAS[sha],
                title="t",
                author="a",
                url="u",
                diff="d",
                diff_truncated=False,
            )
            ids.setdefault((project, sha, kind), set()).add(change.id)
        return repo, ids

    repo, ids = asyncio.run(scenario())

    assert len(repo.persisted_events) == len(set(keys))
    assert all(len(seen) == 1 for seen in ids.values())


def _change() -> Change:
    return Change.new(
        project_id=uuid4(),
        kind=ChangeKind.COMMIT,
        ref="r",
        head_sha="a" * 40,
        title="t",
        author="a",
        url="u",
        diff="d",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )


@given(
    st.lists(
        st.tuples(st.integers(0, 2), st.sampled_from(["agent_1", "agent_2"]), st.integers(1, 3))
    )
)
def test_recording_any_sequence_of_reviews_creates_one_review_and_event_per_distinct_key(
    keys: list[tuple[int, str, int]],
) -> None:
    changes = [_change() for _ in range(3)]

    async def scenario() -> tuple[FakeReviewRepository, dict[tuple, set[UUID]]]:
        repo = FakeReviewRepository()
        ids: dict[tuple, set[UUID]] = {}
        for change_index, agent, run in keys:
            review = await record_review_success(
                repo,
                change=changes[change_index],
                agent=agent,
                run=run,
                result=ReviewResult("r", None, ()),
                raw_output=None,
                duration_ms=1,
            )
            ids.setdefault((change_index, agent, run), set()).add(review.id)
        return repo, ids

    repo, ids = asyncio.run(scenario())

    assert len(repo.persisted_events) == len(set(keys))
    assert all(len(seen) == 1 for seen in ids.values())
