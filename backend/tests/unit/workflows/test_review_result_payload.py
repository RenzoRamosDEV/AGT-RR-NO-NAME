"""El resultado de `run_review` lleva un extracto ACOTADO de lo que respondió el reviewer."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from temporalio.converter import DataConverter

from duelo.application.payload_limits import (
    MAX_ERROR_CHARS,
    MAX_FILE_CHARS,
    MAX_FINDINGS,
    MAX_MESSAGE_CHARS,
    MAX_SUMMARY_CHARS,
)
from duelo.domain.review import Finding, Review, ReviewResult
from duelo.workflows.dto import FindingPayload, RunReviewResult, result_from_review

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _ok(
    findings: tuple[Finding, ...] = (),
    *,
    summary: str = "todo bien",
    raw_output: str | None = None,
) -> Review:
    return Review.succeeded(
        change_id=uuid4(),
        agent="claude",
        run=1,
        result=ReviewResult(summary=summary, score=8, findings=findings),
        raw_output=raw_output,
        duration_ms=1234,
        created_at=NOW,
    )


def test_a_completed_review_carries_what_the_reviewer_answered() -> None:
    review = _ok(
        (
            Finding("bug", "src/app.py", 12, "división por cero"),
            Finding("nit", "N/A", 0, "nombre poco claro"),
        ),
        summary="Cambio pequeño y correcto salvo un caso límite.",
    )

    result = result_from_review(review)

    assert result == RunReviewResult(
        status="completed",
        review_id=str(review.id),
        agent="claude",
        summary="Cambio pequeño y correcto salvo un caso límite.",
        score=8,
        findings=[
            FindingPayload("bug", "src/app.py", 12, "división por cero"),
            FindingPayload("nit", "N/A", 0, "nombre poco claro"),
        ],
        findings_total=2,
        error=None,
        duration_ms=1234,
        truncated=False,
    )


def test_a_failed_review_carries_its_sanitized_error_and_no_findings() -> None:
    review = Review.failed(
        change_id=uuid4(),
        agent="codex",
        run=2,
        error="no hay sesión: token=abc123 caducado",
        duration_ms=50,
        created_at=NOW,
    )

    result = result_from_review(review)

    assert (result.status, result.agent, result.summary, result.score) == (
        "failed",
        "codex",
        None,
        None,
    )
    assert result.error == "no hay sesión: token=[oculto] caducado"
    assert result.findings == [] and result.findings_total == 0
    assert result.duration_ms == 50 and not result.truncated


def test_the_raw_output_of_a_cli_never_reaches_the_payload() -> None:
    secret = "SALIDA-CRUDA-DEL-CLI " * 20
    result = result_from_review(_ok(raw_output=secret))

    assert "SALIDA-CRUDA" not in json.dumps(result, default=lambda o: o.__dict__)
    assert not hasattr(result, "raw_output")


def test_the_summary_is_bounded_and_flagged() -> None:
    result = result_from_review(_ok(summary="x" * (MAX_SUMMARY_CHARS + 500)))

    assert result.summary is not None and len(result.summary) == MAX_SUMMARY_CHARS
    assert result.summary.endswith("…")
    assert result.truncated


def test_a_summary_exactly_at_the_limit_is_not_flagged() -> None:
    result = result_from_review(_ok(summary="x" * MAX_SUMMARY_CHARS))

    assert result.summary == "x" * MAX_SUMMARY_CHARS
    assert not result.truncated


def test_the_findings_are_capped_but_the_real_total_is_kept() -> None:
    many = tuple(Finding("nit", "f.py", i, f"m{i}") for i in range(MAX_FINDINGS + 7))

    result = result_from_review(_ok(many))

    assert len(result.findings) == MAX_FINDINGS
    assert result.findings[-1].message == f"m{MAX_FINDINGS - 1}"
    assert result.findings_total == MAX_FINDINGS + 7
    assert result.truncated


def test_exactly_the_maximum_number_of_findings_is_not_flagged() -> None:
    exact = tuple(Finding("nit", "f.py", i, "m") for i in range(MAX_FINDINGS))

    result = result_from_review(_ok(exact))

    assert len(result.findings) == MAX_FINDINGS and not result.truncated


def test_a_long_message_or_file_is_bounded_and_flagged() -> None:
    result = result_from_review(
        _ok((Finding("bug", "d/" * MAX_FILE_CHARS, 1, "y" * (MAX_MESSAGE_CHARS + 1)),))
    )

    finding = result.findings[0]
    assert len(finding.message) == MAX_MESSAGE_CHARS and finding.message.endswith("…")
    assert len(finding.file) == MAX_FILE_CHARS and finding.file.endswith("…")
    assert result.truncated


def test_a_long_error_is_bounded_and_flagged() -> None:
    review = Review.failed(
        change_id=uuid4(),
        agent="codex",
        run=1,
        error="e" * 1000,
        duration_ms=None,
        created_at=NOW,
    )

    result = result_from_review(review)

    assert result.error is not None and len(result.error) == MAX_ERROR_CHARS
    assert result.truncated and result.duration_ms is None


def test_the_payload_survives_a_round_trip_through_the_temporal_converter() -> None:
    converter = DataConverter.default.payload_converter
    original = result_from_review(_ok((Finding("risk", "a.py", 3, "ojo"),), summary="resumen"))

    payloads = converter.to_payloads([original])
    (restored,) = converter.from_payloads(payloads, [RunReviewResult])

    assert restored == original
    assert isinstance(restored.findings[0], FindingPayload)


def test_a_result_recorded_before_the_extract_existed_still_deserializes() -> None:
    """Un histórico anterior solo tenía `status` y `review_id`: los campos nuevos toman su valor
    por defecto en lugar de romper la deserialización."""
    converter = DataConverter.default.payload_converter
    old = converter.to_payloads([{"status": "completed", "review_id": "abc"}])

    (restored,) = converter.from_payloads(old, [RunReviewResult])

    assert restored == RunReviewResult(status="completed", review_id="abc")
    assert restored.findings == [] and restored.summary is None and not restored.truncated


SECRETS = (
    "abc123tokenvalue",
    "eyJhbGciOiJIUzI1NiJ9.payload",
    "sk-abcdefghijklmnop1234",
    "hunter2",
    "ghp_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5",
)


def _serialized(result: RunReviewResult) -> str:
    return json.dumps(result, default=lambda o: o.__dict__)


def test_a_secret_the_reviewer_quotes_in_a_successful_review_never_reaches_the_history() -> None:
    """Regresión: solo el error de una review fallida se saneaba; el resumen y los hallazgos de
    una review COMPLETADA se copiaban tal cual al historial inmutable de Temporal. Un revisor que
    avisa «hay un token en el diff» lo citaría."""
    review = _ok(
        (
            Finding(
                "bug", "config/sk-abcdefghijklmnop1234.env", 3, "password = hunter2 en el código"
            ),
            Finding(
                "risk",
                "src/app.py",
                9,
                "cabecera Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload",
            ),
            Finding("nit", "src/x.py", 1, "se filtra ghp_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5"),
        ),
        summary="El diff incluye token=abc123tokenvalue y la clave sk-abcdefghijklmnop1234.",
    )

    result = result_from_review(review)

    dumped = _serialized(result)
    for secret in SECRETS:
        assert secret not in dumped, secret
    assert result.summary == "El diff incluye token=[oculto] y la clave [oculto]."
    assert result.findings[0].message == "password = [oculto] en el código"
    assert result.findings[0].file == "config/[oculto].env"
    assert result.findings[1].message == "cabecera Authorization: [oculto]"


def test_redaction_does_not_count_as_truncation() -> None:
    result = result_from_review(_ok(summary="token=abc123tokenvalue"))

    assert result.summary == "token=[oculto]"
    assert not result.truncated


def test_a_secret_in_the_severity_is_hidden_too() -> None:
    result = result_from_review(_ok((Finding("token=abc123tokenvalue", "f.py", 1, "m"),)))

    assert "abc123tokenvalue" not in _serialized(result)
