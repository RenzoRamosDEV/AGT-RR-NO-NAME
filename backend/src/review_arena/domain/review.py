from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


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
