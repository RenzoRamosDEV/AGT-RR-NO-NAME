from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from duelo.application.ingest_commit import ChangeSubmission
from duelo.application.read_models import AgentStats, ChangeDetail, ChangePage, ChangeSummary
from duelo.domain.change import MAX_HEAD_SHA, MAX_REF, MAX_URL, ChangeKind, ChangeStatus
from duelo.domain.project import Project
from duelo.domain.review import Finding, Review, ReviewStatus
from duelo.domain.review_status import ChangeReviewStatus, FindingsSummary


class IngestCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1, max_length=255)
    ref: str = Field(min_length=1, max_length=MAX_REF)
    head_sha: str = Field(min_length=1, max_length=MAX_HEAD_SHA)
    title: str = ""
    author: str = ""
    url: str = Field(default="", max_length=MAX_URL)
    diff: str = ""

    @field_validator("project")
    @classmethod
    def _project_has_no_nul(cls, value: str) -> str:
        # Postgres no admite NUL en texto: sin esto la consulta del slug acabaría en un 500.
        if "\x00" in value:
            raise ValueError("project no puede contener caracteres NUL")
        return value

    def to_submission(self) -> ChangeSubmission:
        return ChangeSubmission(**self.model_dump())


class IngestCommitResponse(BaseModel):
    change_id: UUID
    diff_truncated: bool


class IngestPrRequest(IngestCommitRequest):
    """Mismos campos y límites que un commit: `ref` es la rama o `refs/pull/N/head` y
    `head_sha` el último commit de la cabeza del PR."""


class IngestPrResponse(IngestCommitResponse):
    pass


class ProjectResponse(BaseModel):
    id: UUID
    slug: str

    @classmethod
    def from_domain(cls, project: Project) -> ProjectResponse:
        return cls(id=project.id, slug=project.slug)


class ChangeSummaryResponse(BaseModel):
    id: UUID
    project_id: UUID
    kind: ChangeKind
    ref: str
    head_sha: str
    title: str
    author: str
    url: str
    diff_truncated: bool
    status: ChangeStatus
    review_status: ChangeReviewStatus
    run: int
    created_at: datetime

    @classmethod
    def from_summary(cls, change: ChangeSummary) -> ChangeSummaryResponse:
        return cls(
            id=change.id,
            project_id=change.project_id,
            kind=change.kind,
            ref=change.ref,
            head_sha=change.head_sha,
            title=change.title,
            author=change.author,
            url=change.url,
            diff_truncated=change.diff_truncated,
            status=change.status,
            review_status=change.review_status,
            run=change.run,
            created_at=change.created_at,
        )


class ChangePageResponse(BaseModel):
    items: list[ChangeSummaryResponse]
    next_cursor: str | None = None

    @classmethod
    def from_page(cls, page: ChangePage, next_cursor: str | None) -> ChangePageResponse:
        return cls(
            items=[ChangeSummaryResponse.from_summary(c) for c in page.items],
            next_cursor=next_cursor,
        )


class FindingResponse(BaseModel):
    severity: str
    file: str
    line: int
    message: str

    @classmethod
    def from_domain(cls, finding: Finding) -> FindingResponse:
        return cls(
            severity=finding.severity,
            file=finding.file,
            line=finding.line,
            message=finding.message,
        )


class ReviewResponse(BaseModel):
    """Una review sin su `raw_output`: es salida cruda del agente y puede ser enorme."""

    id: UUID
    agent: str
    run: int
    status: ReviewStatus
    summary: str | None
    score: int | None
    findings: list[FindingResponse]
    duration_ms: int | None
    error: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, review: Review) -> ReviewResponse:
        return cls(
            id=review.id,
            agent=review.agent,
            run=review.run,
            status=review.status,
            summary=review.summary,
            score=review.score,
            findings=[FindingResponse.from_domain(f) for f in review.findings],
            duration_ms=review.duration_ms,
            error=review.error,
            created_at=review.created_at,
        )


class SeverityCountsResponse(BaseModel):
    bug: int
    risk: int
    improvement: int
    nit: int
    other: int


class FindingsSummaryResponse(BaseModel):
    """Findings del run actual con las severidades normalizadas (`other`: no reconocidas)."""

    total: int
    by_severity: SeverityCountsResponse

    @classmethod
    def from_domain(cls, summary: FindingsSummary) -> FindingsSummaryResponse:
        return cls(
            total=summary.total,
            by_severity=SeverityCountsResponse(
                bug=summary.bug,
                risk=summary.risk,
                improvement=summary.improvement,
                nit=summary.nit,
                other=summary.other,
            ),
        )


class ChangeDetailResponse(ChangeSummaryResponse):
    diff: str
    reviews: list[ReviewResponse]
    findings_summary: FindingsSummaryResponse

    @classmethod
    def from_detail(cls, detail: ChangeDetail) -> ChangeDetailResponse:
        change = detail.change
        return cls(
            id=change.id,
            project_id=change.project_id,
            kind=change.kind,
            ref=change.ref,
            head_sha=change.head_sha,
            title=change.title,
            author=change.author,
            url=change.url,
            diff_truncated=change.diff_truncated,
            status=change.status,
            review_status=detail.review_status,
            run=change.run,
            created_at=change.created_at,
            diff=change.diff,
            reviews=[ReviewResponse.from_domain(r) for r in detail.reviews],
            findings_summary=FindingsSummaryResponse.from_domain(detail.findings_summary),
        )


class AgentStatsResponse(BaseModel):
    agent: str
    total: int
    completed: int
    failed: int
    avg_duration_ms: float | None
    avg_score: float | None

    @classmethod
    def from_domain(cls, stats: AgentStats) -> AgentStatsResponse:
        return cls(
            agent=stats.agent,
            total=stats.total,
            completed=stats.completed,
            failed=stats.failed,
            avg_duration_ms=stats.avg_duration_ms,
            avg_score=stats.avg_score,
        )


class RetryReviewResponse(BaseModel):
    change_id: UUID
    run: int


class DependencyHealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    latency_ms: int
    # Vocabulario cerrado: nunca el texto de la excepción (puede llevar credenciales).
    reason: Literal["timeout", "error"] | None = None


class DependenciesHealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    dependencies: dict[str, DependencyHealthResponse]


class ErrorResponse(BaseModel):
    detail: str
