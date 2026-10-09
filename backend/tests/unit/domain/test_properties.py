"""Propiedades (hypothesis) de las entidades y de los payloads de eventos.

Se usa property-based solo donde la propiedad es más clara que un ejemplo: invariantes de
campos, límites y serialización de payloads.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from duelo.domain.change import (
    MAX_AUTHOR,
    MAX_HEAD_SHA,
    MAX_REF,
    MAX_TITLE,
    MAX_URL,
    Change,
    ChangeKind,
)
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.review import MAX_AGENT, Review, ReviewResult, ReviewStatus

NO_NUL = st.characters(blacklist_characters="\x00")
CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def identifier(limit: int) -> st.SearchStrategy[str]:
    return st.text(NO_NUL, min_size=1, max_size=limit)


def _new(**overrides: object) -> Change:
    fields: dict[str, object] = {
        "project_id": uuid4(),
        "kind": ChangeKind.COMMIT,
        "ref": "refs/heads/main",
        "head_sha": "a" * 40,
        "title": "t",
        "author": "a",
        "url": "https://example.com",
        "diff": "d",
        "diff_truncated": False,
        "created_at": CREATED_AT,
    }
    fields.update(overrides)
    return Change.new(**fields)  # type: ignore[arg-type]


@given(
    head_sha=identifier(MAX_HEAD_SHA),
    ref=identifier(MAX_REF),
    url=identifier(MAX_URL),
    title=st.text(max_size=MAX_TITLE + 80),
    author=st.text(max_size=MAX_AUTHOR + 80),
    diff=st.text(max_size=300),
    kind=st.sampled_from(ChangeKind),
)
def test_valid_input_is_preserved_and_display_fields_are_prefix_truncated(
    head_sha: str, ref: str, url: str, title: str, author: str, diff: str, kind: ChangeKind
) -> None:
    change = _new(
        head_sha=head_sha, ref=ref, url=url, title=title, author=author, diff=diff, kind=kind
    )

    assert (change.head_sha, change.ref, change.url, change.diff, change.kind) == (
        head_sha,
        ref,
        url,
        diff,
        kind,
    )
    assert change.title == title[:MAX_TITLE]
    assert change.author == author[:MAX_AUTHOR]
    assert len(change.title) <= MAX_TITLE and len(change.author) <= MAX_AUTHOR


@given(
    field=st.sampled_from([("head_sha", MAX_HEAD_SHA), ("ref", MAX_REF), ("url", MAX_URL)]),
    extra=st.integers(min_value=1, max_value=50),
)
def test_identifiers_over_the_limit_are_always_rejected(field: tuple[str, int], extra: int) -> None:
    name, limit = field

    with pytest.raises(ValueError, match=name):
        _new(**{name: "x" * (limit + extra)})


@given(
    name=st.sampled_from(["head_sha", "ref", "url"]),
    prefix=st.text(NO_NUL, max_size=5),
    suffix=st.text(NO_NUL, max_size=5),
)
def test_a_nul_inside_any_identifier_is_always_rejected(
    name: str, prefix: str, suffix: str
) -> None:
    with pytest.raises(ValueError, match=name):
        _new(**{name: f"{prefix}\x00{suffix}" or "\x00"})


@given(agent=st.text(NO_NUL, min_size=1, max_size=MAX_AGENT), error=st.text(min_size=1))
def test_review_constructors_always_produce_coherent_states(agent: str, error: str) -> None:
    ok = Review.succeeded(
        change_id=uuid4(),
        agent=agent,
        run=1,
        result=ReviewResult("r", None, ()),
        raw_output=None,
        duration_ms=0,
        created_at=CREATED_AT,
    )
    failed = Review.failed(
        change_id=uuid4(), agent=agent, run=1, error=error, duration_ms=None, created_at=CREATED_AT
    )

    assert (ok.status, ok.error, ok.agent) == (ReviewStatus.COMPLETED, None, agent)
    assert (failed.status, failed.summary, failed.error) == (ReviewStatus.FAILED, None, error)


uuids = st.uuids()


@given(change_id=uuids, project_id=uuids, kind=st.sampled_from(["commit", "pr"]), sha=st.text())
def test_change_created_payload_is_json_serializable_and_roundtrips(
    change_id: UUID, project_id: UUID, kind: str, sha: str
) -> None:
    payload = ChangeCreated(change_id, project_id, kind, sha).to_payload()

    assert json.loads(json.dumps(payload)) == payload
    assert (payload["change_id"], payload["project_id"]) == (str(change_id), str(project_id))


@given(review_id=uuids, change_id=uuids, project_id=uuids, agent=st.text(), error=st.text())
def test_review_event_payloads_are_json_serializable_and_roundtrip(
    review_id: UUID, change_id: UUID, project_id: UUID, agent: str, error: str
) -> None:
    completed = ReviewCompleted(review_id, change_id, project_id, agent).to_payload()
    failed = ReviewFailed(review_id, change_id, project_id, agent, error).to_payload()

    for payload in (completed, failed):
        assert json.loads(json.dumps(payload)) == payload
        assert payload["review_id"] == str(review_id)
    assert failed["error"] == error
    assert "error" not in completed
