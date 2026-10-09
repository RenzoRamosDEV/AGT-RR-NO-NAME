from datetime import UTC, datetime
from uuid import uuid4

import pytest

from review_arena.domain.change import Change, ChangeKind, ChangeStatus


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
