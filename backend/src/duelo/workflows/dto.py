"""Entradas/salidas serializables de workflows y activities.

Regla binding (openspec/config.yaml): por Temporal viajan IDs, valores primitivos y, del resultado
de una review, un extracto ACOTADO (resumen, nota, hallazgos y error saneado), nunca datos pesados
como el diff o la salida cruda de un CLI: el historial de Temporal tiene un límite de 2 MB por
payload y se guarda entero. Cada workflow y activity recibe un único argumento dataclass para poder
añadir campos sin romper ejecuciones en curso; los campos nuevos llevan siempre un valor por defecto
para que los históricos anteriores se sigan deserializando.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from duelo.application.payload_limits import (
    MAX_FILE_CHARS,
    MAX_FINDINGS,
    MAX_MESSAGE_CHARS,
    MAX_SEVERITY_CHARS,
    MAX_SUMMARY_CHARS,
    bound_error,
    bound_redacted,
)
from duelo.application.review_requests import ReviewCommitInput
from duelo.domain.review import Review

__all__ = [
    "FindingPayload",
    "ReviewChangeInput",
    "ReviewCommitInput",
    "RunReviewInput",
    "RunReviewResult",
    "result_from_review",
]


@dataclass
class RunReviewInput:
    change_id: str
    agent_name: str
    run: int


@dataclass
class FindingPayload:
    severity: str = ""
    file: str = ""
    line: int = 0
    message: str = ""


@dataclass
class RunReviewResult:
    """Lo que devuelve la activity: el estado y el id (como siempre) más un extracto acotado de la
    respuesta del reviewer, para leerla en el historial de Temporal sin ir a la base de datos."""

    status: str
    review_id: str
    agent: str = ""
    summary: str | None = None
    score: int | None = None
    findings: list[FindingPayload] = field(default_factory=list)
    # Hallazgos que tenía la review; `findings` lleva como mucho `MAX_FINDINGS`.
    findings_total: int = 0
    # Motivo del fallo, ya saneado (sin credenciales) y acotado.
    error: str | None = None
    duration_ms: int | None = None
    # `True` si se cortó algún texto o se descartaron hallazgos para respetar los límites.
    truncated: bool = False


@dataclass
class ReviewChangeInput:
    change_id: str
    agent_names: list[str]
    run: int = 1
    head_sha: str = ""


def result_from_review(review: Review) -> RunReviewResult:
    """Extracto acotado de `review` para el resultado de la activity. No incluye `raw_output` y todo
    el texto libre (resumen, hallazgos, error) sale sin credenciales: el historial de Temporal es
    inmutable y lo que entra ahí no se puede borrar."""
    truncated = False
    summary: str | None = None
    if review.summary is not None:
        summary, cut = bound_redacted(review.summary, MAX_SUMMARY_CHARS)
        truncated = truncated or cut

    findings: list[FindingPayload] = []
    for finding in review.findings[:MAX_FINDINGS]:
        message, cut_message = bound_redacted(finding.message, MAX_MESSAGE_CHARS)
        file, cut_file = bound_redacted(finding.file, MAX_FILE_CHARS)
        severity, cut_severity = bound_redacted(finding.severity, MAX_SEVERITY_CHARS)
        truncated = truncated or cut_message or cut_file or cut_severity
        findings.append(
            FindingPayload(severity=severity, file=file, line=finding.line, message=message)
        )
    if len(review.findings) > MAX_FINDINGS:
        truncated = True

    error: str | None = None
    if review.error is not None:
        error, cut = bound_error(review.error)
        truncated = truncated or cut

    return RunReviewResult(
        status=review.status.value,
        review_id=str(review.id),
        agent=review.agent,
        summary=summary,
        score=review.score,
        findings=findings,
        findings_total=len(review.findings),
        error=error,
        duration_ms=review.duration_ms,
        truncated=truncated,
    )
