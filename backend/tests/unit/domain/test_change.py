from datetime import UTC, datetime
from uuid import uuid4

import pytest

from duelo.domain.change import Change, ChangeKind, ChangeStatus


def test_new_change_is_valid() -> None:
    change = Change.new(
        project_id=uuid4(),
        kind=ChangeKind.COMMIT,
        ref="refs/heads/main",
        head_sha="a" * 40,
        title="fix: algo",
        author="renzo",
        url="https://github.com/example/repo/commit/abc",
        diff="diff --git a/x b/x",
        diff_truncated=False,
        created_at=datetime.now(UTC),
    )

    assert change.kind is ChangeKind.COMMIT
    assert change.status is ChangeStatus.PENDING
    assert change.status == "pending"
    assert change.run == 1


def test_change_requires_a_head_sha() -> None:
    with pytest.raises(ValueError):
        Change.new(
            project_id=uuid4(),
            kind=ChangeKind.COMMIT,
            ref="refs/heads/main",
            head_sha="",
            title="fix: algo",
            author="renzo",
            url="https://github.com/example/repo/commit/abc",
            diff="diff --git a/x b/x",
            diff_truncated=False,
            created_at=datetime.now(UTC),
        )


def _new(**overrides: object) -> Change:
    fields: dict[str, object] = {
        "project_id": uuid4(),
        "kind": ChangeKind.COMMIT,
        "ref": "refs/heads/main",
        "head_sha": "a" * 40,
        "title": "fix: algo",
        "author": "renzo",
        "url": "https://github.com/example/repo/commit/abc",
        "diff": "diff --git a/x b/x\n@@ -1 +1 @@\n-a\n+b\n+c\n",
        "diff_truncated": False,
        "created_at": datetime.now(UTC),
    }
    fields.update(overrides)
    return Change.new(**fields)  # type: ignore[arg-type]


def test_new_change_carries_the_summary_of_its_diff() -> None:
    summary = _new().diff_summary

    assert (summary.files_changed, summary.additions, summary.deletions) == (1, 2, 1)


def test_new_change_with_an_empty_diff_has_an_empty_summary() -> None:
    assert _new(diff="").diff_summary.files_changed == 0


def test_the_id_can_be_chosen_and_defaults_to_a_fresh_one() -> None:
    chosen = uuid4()

    assert _new(id=chosen).id == chosen
    assert _new().id != _new().id
