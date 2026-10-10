from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

# Límite de negocio; coincide con la columna `reviews.agent` (un test lo garantiza).
MAX_AGENT = 50


def _validate_agent(agent: str) -> None:
    if not agent:
        raise ValueError("agent no puede estar vacío")
    if len(agent) > MAX_AGENT:
        raise ValueError(f"agent no puede superar {MAX_AGENT} caracteres (recibidos {len(agent)})")


class ReviewStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Finding:
    severity: str
    file: str
    line: int
    message: str


@dataclass(frozen=True, slots=True)
class ReviewResult:
    summary: str
    score: int | None
    findings: tuple[Finding, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Review:
    id: UUID
    change_id: UUID
    agent: str
    run: int
    status: ReviewStatus
    summary: str | None
    score: int | None
    findings: tuple[Finding, ...]
    raw_output: str | None
    duration_ms: int | None
    error: str | None
    created_at: datetime
    # Change del que se copió esta review (la PR reutiliza las de su commit idéntico); `None` en
    # las que hizo un agente.
    reused_from_change_id: UUID | None = None

    @classmethod
    def reused_from(cls, source: Review, *, change_id: UUID, created_at: datetime) -> Review:
        """Copia de una review completada de otro change para `change_id` (siempre `run` 1).

        Lleva el resultado (resumen, nota, hallazgos, duración) pero no la salida cruda ni el
        error: la copia no es una ejecución, solo el veredicto."""
        if source.status is not ReviewStatus.COMPLETED:
            raise ValueError("solo se reutilizan reviews completadas")
        return cls(
            id=uuid4(),
            change_id=change_id,
            agent=source.agent,
            run=1,
            status=ReviewStatus.COMPLETED,
            summary=source.summary,
            score=source.score,
            findings=source.findings,
            raw_output=None,
            duration_ms=source.duration_ms,
            error=None,
            created_at=created_at,
            reused_from_change_id=source.change_id,
        )

    @classmethod
    def succeeded(
        cls,
        *,
        change_id: UUID,
        agent: str,
        run: int,
        result: ReviewResult,
        raw_output: str | None,
        duration_ms: int,
        created_at: datetime,
    ) -> Review:
        _validate_agent(agent)
        return cls(
            id=uuid4(),
            change_id=change_id,
            agent=agent,
            run=run,
            status=ReviewStatus.COMPLETED,
            summary=result.summary,
            score=result.score,
            findings=result.findings,
            raw_output=raw_output,
            duration_ms=duration_ms,
            error=None,
            created_at=created_at,
        )

    @classmethod
    def failed(
        cls,
        *,
        change_id: UUID,
        agent: str,
        run: int,
        error: str,
        duration_ms: int | None,
        created_at: datetime,
    ) -> Review:
        _validate_agent(agent)
        if not error:
            raise ValueError("error no puede estar vacío en una review fallida")
        return cls(
            id=uuid4(),
            change_id=change_id,
            agent=agent,
            run=run,
            status=ReviewStatus.FAILED,
            summary=None,
            score=None,
            findings=(),
            raw_output=None,
            duration_ms=duration_ms,
            error=error,
            created_at=created_at,
        )
