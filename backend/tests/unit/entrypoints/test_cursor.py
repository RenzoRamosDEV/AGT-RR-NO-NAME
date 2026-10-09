from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from duelo.application.read_models import ChangeCursor
from duelo.entrypoints.api.cursor import InvalidCursor, decode_cursor, encode_cursor


@given(
    st.datetimes(timezones=st.sampled_from([UTC, timezone(timedelta(hours=2))])),
    st.uuids(),
)
def test_encoding_then_decoding_gives_back_the_same_cursor(created_at: datetime, uid) -> None:
    cursor = ChangeCursor(created_at=created_at, id=uid)

    assert decode_cursor(encode_cursor(cursor)) == cursor


def test_the_encoded_cursor_is_url_safe_without_padding() -> None:
    encoded = encode_cursor(ChangeCursor(created_at=datetime.now(UTC), id=uuid4()))

    assert encoded and all(c.isalnum() or c in "-_" for c in encoded)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "no es un cursor",
        "!!!!",
        "////",  # base64 estándar, no url-safe
        "YWJj",  # decodifica a "abc": sin separador
        "fA",  # solo "|"
        "MjAyNi0wMS0wMVQwMDowMDowMHxub3QtYS11dWlk",  # fecha válida, uuid inválido
        "bm8tZGF0ZXwwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDA",  # fecha inválida
        "MjAyNi0wMS0wMVQwMDowMDowMHwwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDA",  # sin zona
        "_w",  # bytes no UTF-8
        "YXxifGM",  # demasiadas partes
    ],
)
def test_malformed_cursors_are_rejected(value: str) -> None:
    with pytest.raises(InvalidCursor):
        decode_cursor(value)
