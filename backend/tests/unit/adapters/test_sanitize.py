"""Saneado de NUL antes de persistir: ejemplos explícitos + propiedades (hypothesis)."""

from hypothesis import given
from hypothesis import strategies as st

from duelo.adapters.persistence.sanitize import sanitize_json, sanitize_text

NUL = "\x00"
REPLACEMENT = "�"

json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda children: (
        st.lists(children, max_size=4) | st.dictionaries(st.text(max_size=8), children, max_size=4)
    ),
    max_leaves=12,
)


def _contains_nul(value: object) -> bool:
    if isinstance(value, str):
        return NUL in value
    if isinstance(value, list):
        return any(_contains_nul(v) for v in value)
    if isinstance(value, dict):
        return any(_contains_nul(k) or _contains_nul(v) for k, v in value.items())
    return False


def _shape(value: object) -> object:
    if isinstance(value, list):
        return [_shape(v) for v in value]
    if isinstance(value, dict):
        return {k.replace(NUL, REPLACEMENT): _shape(v) for k, v in value.items()}
    return type(value).__name__


def test_replaces_each_nul_with_the_replacement_character() -> None:
    assert sanitize_text("a\x00b\x00") == "a�b�"


def test_none_passes_through() -> None:
    assert sanitize_text(None) is None


@given(st.text())
def test_text_never_contains_nul(text: str) -> None:
    assert NUL not in sanitize_text(text)


@given(st.text())
def test_text_sanitizing_is_idempotent(text: str) -> None:
    once = sanitize_text(text)
    assert sanitize_text(once) == once


@given(st.text().filter(lambda t: NUL not in t))
def test_text_without_nul_is_unchanged(text: str) -> None:
    assert sanitize_text(text) == text


@given(st.text())
def test_text_length_is_preserved(text: str) -> None:
    assert len(sanitize_text(text)) == len(text)


@given(json_values)
def test_json_never_contains_nul_and_keeps_its_shape(value: object) -> None:
    cleaned = sanitize_json(value)

    assert not _contains_nul(cleaned)
    assert _shape(cleaned) == _shape(value)
