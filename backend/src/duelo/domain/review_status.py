"""Estado agregado de las reviews de un change y normalización de severidades.

Son reglas puras sobre contadores y cadenas: el listado las alimenta desde una consulta
agregada (sin cargar reviews) y el detalle desde las reviews ya cargadas."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from duelo.domain.review import Review, ReviewStatus


class ChangeReviewStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"
    COMPLETED = "completed"


def review_status_from_counts(
    *, completed: int, failed: int, expected_agents: int
) -> ChangeReviewStatus:
    """Estado de un change a partir de las reviews de su `run` actual.

    `running` mientras falten agentes por registrar: una review fallida no cierra el estado
    si otro agente aún puede completarse."""
    total = completed + failed
    if total == 0:
        return ChangeReviewStatus.PENDING
    if total < expected_agents:
        return ChangeReviewStatus.RUNNING
    if failed == 0:
        return ChangeReviewStatus.COMPLETED
    if completed == 0:
        return ChangeReviewStatus.FAILED
    return ChangeReviewStatus.PARTIAL_FAILED


def review_status_of_run(
    run: int, reviews: Iterable[Review], *, expected_agents: int
) -> ChangeReviewStatus:
    """Igual, sobre las reviews ya cargadas: solo cuentan las del `run` indicado (las de
    ejecuciones anteriores quedaron superadas)."""
    current = [r for r in reviews if r.run == run]
    return review_status_from_counts(
        completed=sum(r.status is ReviewStatus.COMPLETED for r in current),
        failed=sum(r.status is ReviewStatus.FAILED for r in current),
        expected_agents=expected_agents,
    )


# Se puede reintentar cuando la ejecución actual ya terminó con algún fallo. Una review
# completada nunca se relanza: gastaría a los agentes otra vez.
RETRYABLE_STATUSES = frozenset({ChangeReviewStatus.FAILED, ChangeReviewStatus.PARTIAL_FAILED})


class Severity(StrEnum):
    BUG = "bug"
    RISK = "risk"
    IMPROVEMENT = "improvement"
    NIT = "nit"
    OTHER = "other"


_SYNONYMS: dict[str, Severity] = {
    "bug": Severity.BUG,
    "error": Severity.BUG,
    "critical": Severity.BUG,
    "blocker": Severity.BUG,
    "high": Severity.BUG,
    "risk": Severity.RISK,
    "warning": Severity.RISK,
    "warn": Severity.RISK,
    "medium": Severity.RISK,
    "major": Severity.RISK,
    "security": Severity.RISK,
    "improvement": Severity.IMPROVEMENT,
    "suggestion": Severity.IMPROVEMENT,
    "enhancement": Severity.IMPROVEMENT,
    "refactor": Severity.IMPROVEMENT,
    "nit": Severity.NIT,
    "nitpick": Severity.NIT,
    "style": Severity.NIT,
    "low": Severity.NIT,
    "minor": Severity.NIT,
    "info": Severity.NIT,
}


def normalize_severity(raw: str) -> Severity:
    """Las severidades guardadas son cadenas libres: se normalizan al leer, sin tocar los datos."""
    return _SYNONYMS.get(raw.strip().lower(), Severity.OTHER)


@dataclass(frozen=True, slots=True)
class FindingsSummary:
    total: int
    bug: int
    risk: int
    improvement: int
    nit: int
    other: int


def summarize_severities(severities: Iterable[str]) -> FindingsSummary:
    counts = dict.fromkeys(Severity, 0)
    for raw in severities:
        counts[normalize_severity(raw)] += 1
    return FindingsSummary(
        total=sum(counts.values()),
        bug=counts[Severity.BUG],
        risk=counts[Severity.RISK],
        improvement=counts[Severity.IMPROVEMENT],
        nit=counts[Severity.NIT],
        other=counts[Severity.OTHER],
    )
