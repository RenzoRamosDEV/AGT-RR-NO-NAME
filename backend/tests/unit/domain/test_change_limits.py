"""Particiones de equivalencia y valores límite de Change.new (spec change-ingestion)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from review_arena.domain.change import (
    MAX_AUTHOR,
    MAX_HEAD_SHA,
    MAX_REF,
    MAX_TITLE,
    MAX_URL,
    Change,
    ChangeKind,
)


def _new(**overrides: object) -> Change:
    fields: dict[str, object] = {
        "project_id": uuid4(),
        "kind": ChangeKind.COMMIT,
        "ref": "refs/heads/main",
        "head_sha": "a" * 40,
        "title": "fix: algo",
        "author": "renzo",
        "url": "https://example.com/commit/a",
        "diff": "diff --git a/x b/x",
        "diff_truncated": False,
        "created_at": datetime.now(UTC),
    }
    fields.update(overrides)
    return Change.new(**fields)  # type: ignore[arg-type]


def test_limits_match_the_documented_values() -> None:
    assert (MAX_HEAD_SHA, MAX_REF, MAX_URL, MAX_TITLE, MAX_AUTHOR) == (64, 255, 1000, 500, 255)


@pytest.mark.parametrize(
    ("field", "limit"),
    [("head_sha", MAX_HEAD_SHA), ("ref", MAX_REF), ("url", MAX_URL)],
)
class TestIdentifierBoundaries:
    def test_accepts_one_below_and_exactly_the_limit(self, field: str, limit: int) -> None:
        for length in (1, limit - 1, limit):
            assert getattr(_new(**{field: "x" * length}), field) == "x" * length

    def test_rejects_one_over_the_limit_naming_the_field(self, field: str, limit: int) -> None:
        with pytest.raises(ValueError, match=field):
            _new(**{field: "x" * (limit + 1)})

    def test_rejects_nul_naming_the_field(self, field: str, limit: int) -> None:
        with pytest.raises(ValueError, match=field):
            _new(**{field: "ab\x00cd"})


def test_head_sha_cannot_be_empty() -> None:
    with pytest.raises(ValueError, match="head_sha"):
        _new(head_sha="")


@pytest.mark.parametrize(("field", "limit"), [("title", MAX_TITLE), ("author", MAX_AUTHOR)])
class TestDisplayMetadataIsTruncatedNotRejected:
    def test_values_up_to_the_limit_are_kept_intact(self, field: str, limit: int) -> None:
        for length in (0, 1, limit - 1, limit):
            assert getattr(_new(**{field: "y" * length}), field) == "y" * length

    def test_longer_values_are_truncated_to_a_prefix_of_the_limit(
        self, field: str, limit: int
    ) -> None:
        original = "".join(chr(ord("a") + i % 26) for i in range(limit + 37))

        truncated = getattr(_new(**{field: original}), field)

        assert len(truncated) == limit
        assert original.startswith(truncated)


class TestExactValidationMessages:
    """El mensaje es el contrato con quien llama (la API lo mostrará): se comprueba entero."""

    def test_empty_head_sha(self) -> None:
        with pytest.raises(ValueError) as error:
            _new(head_sha="")
        assert str(error.value) == "head_sha no puede estar vacío"

    @pytest.mark.parametrize(
        ("field", "limit"),
        [("head_sha", MAX_HEAD_SHA), ("ref", MAX_REF), ("url", MAX_URL)],
    )
    def test_too_long_identifier(self, field: str, limit: int) -> None:
        with pytest.raises(ValueError) as error:
            _new(**{field: "x" * (limit + 2)})
        assert (
            str(error.value)
            == f"{field} no puede superar {limit} caracteres (recibidos {limit + 2})"
        )

    @pytest.mark.parametrize("field", ["head_sha", "ref", "url"])
    def test_nul_in_identifier(self, field: str) -> None:
        with pytest.raises(ValueError) as error:
            _new(**{field: "a\x00b"})
        assert str(error.value) == f"{field} no puede contener el carácter NUL"
