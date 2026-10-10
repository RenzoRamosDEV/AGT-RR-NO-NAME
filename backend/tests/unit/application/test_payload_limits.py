"""Límites y saneado de lo que se copia de una review al historial de Temporal."""

from __future__ import annotations

import pytest

from duelo.application.payload_limits import (
    MAX_ERROR_CHARS,
    bound,
    bound_error,
    bound_redacted,
    redact_secrets,
)


def test_a_short_text_goes_through_untouched() -> None:
    assert bound("hola", 10) == ("hola", False)
    assert bound("a" * 10, 10) == ("a" * 10, False)


def test_a_long_text_is_cut_at_the_limit_and_flagged() -> None:
    cut, truncated = bound("a" * 11, 10)
    assert truncated
    assert cut == "a" * 9 + "…"
    assert len(cut) == 10


def test_line_breaks_and_tabs_survive_but_other_control_characters_do_not() -> None:
    assert bound("uno\ndos\ttres\x00\x07\x1b[0m", 100)[0] == "uno\ndos\ttres   [0m"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("falló con token=abc123 al conectar", "falló con token=[oculto] al conectar"),
        ("PASSWORD: hunter2", "PASSWORD: [oculto]"),
        ("api_key = xyz", "api_key = [oculto]"),
        ("api-key=xyz", "api-key=[oculto]"),
        ("Authorization: Bearer eyJhbGci.abc", "Authorization: [oculto]"),
        ("cabecera Bearer abc.def", "cabecera Bearer [oculto]"),
        ("usa sk-abcdefgh1234 aquí", "usa [oculto] aquí"),
        ("sk-corta no es clave", "sk-corta no es clave"),
        ("nada que ocultar", "nada que ocultar"),
    ],
)
def test_what_looks_like_a_credential_is_hidden(raw: str, expected: str) -> None:
    assert redact_secrets(raw) == expected


def test_an_error_is_redacted_before_it_is_bounded() -> None:
    error, truncated = bound_error("fallo con token=" + "s" * 1000)

    assert error == "fallo con token=[oculto]"
    assert not truncated


def test_a_long_error_is_cut_and_flagged() -> None:
    error, truncated = bound_error("x" * 1000)

    assert truncated
    assert len(error) == MAX_ERROR_CHARS
    assert error.endswith("…")


def test_a_cut_text_does_not_keep_the_space_before_the_ellipsis() -> None:
    assert bound("abcd efgh", 6) == ("abcd…", True)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("token de GitHub ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5", "token de GitHub [oculto]"),
        ("clave AKIAIOSFODNN7EXAMPLE en el diff", "clave [oculto] en el diff"),
        ("webhook xoxb-123456789012-abcdefghij", "webhook [oculto]"),
        (
            # Troceado: un JWT entero en el código lo marcaría el escáner de secretos.
            "jwt "
            + ".".join(("eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiIxMjM0In0", "c2lnbmF0dXJl"))
            + " fin",
            "jwt [oculto] fin",
        ),
        (
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----",
            "[oculto]",
        ),
        ('password = "hunter2" en el código', "password = [oculto] en el código"),
        ("Basic auth: Authorization: Basic dXNlcjpwYXNz", "Basic auth: Authorization: [oculto]"),
    ],
)
def test_the_credentials_a_reviewer_may_quote_from_the_diff_are_hidden(
    raw: str, expected: str
) -> None:
    assert redact_secrets(raw) == expected


def test_bound_redacted_hides_the_secret_before_cutting_so_no_half_secret_survives() -> None:
    """Se redacta ANTES de cortar: si se cortara primero, un `sk-…` partido por el límite ya no
    casaría con el patrón y su principio quedaría a la vista."""
    text = "x" * 8 + " sk-abcdefghijklmnop1234"

    cut, truncated = bound_redacted(text, 20)

    assert "sk-" not in cut and "abcdef" not in cut
    assert cut == "x" * 8 + " [oculto]"
    assert not truncated


def test_bound_redacted_still_bounds_and_flags() -> None:
    assert bound_redacted("a" * 11, 10) == ("a" * 9 + "…", True)
