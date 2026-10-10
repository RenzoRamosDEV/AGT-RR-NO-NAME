from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from duelo.application.ingest_commit import ChangeSubmission
from duelo.application.read_models import (
    AgentStats,
    ChangeDetail,
    ChangeEvent,
    ChangePage,
    ChangeSummary,
    RawOutput,
    RevertRef,
    ReviewBrief,
)
from duelo.domain.change import MAX_HEAD_SHA, MAX_REF, MAX_URL, ChangeKind, ChangeStatus
from duelo.domain.commit_state import CommitState
from duelo.domain.diff import DiffSummary
from duelo.domain.project import Project
from duelo.domain.review import Finding, Review, ReviewStatus
from duelo.domain.review_status import ChangeReviewStatus, FindingsSummary

# Sin NUL: Postgres no lo admite en texto. Al ir en el esquema, el contrato lo declara y el 422 es
# el estándar de FastAPI (no un caso especial del handler).
NO_NUL = r"^[^\x00]*$"

# Cuerpo del mensaje de un commit: solo se lee para detectar `This reverts commit <sha>` y no se
# guarda. El hook lo envía recortado a 4 000 caracteres; este es el tope que admite la API.
MAX_BODY = 20_000


class IngestCommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1, max_length=255)
    ref: str = Field(min_length=1, max_length=MAX_REF)
    head_sha: str = Field(min_length=1, max_length=MAX_HEAD_SHA)
    title: str = ""
    author: str = ""
    url: str = Field(default="", max_length=MAX_URL)
    diff: str = ""
    # Opcional: los hooks anteriores a este campo no lo envían y todo sigue igual.
    body: str = Field(default="", max_length=MAX_BODY)

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
    # `False` si el change ya existía (reingesta idempotente); el estado sigue siendo 202.
    created: bool


class IngestPrRequest(IngestCommitRequest):
    """Mismos campos y límites que un commit: `ref` es la rama o `refs/pull/N/head` y
    `head_sha` el último commit de la cabeza del PR."""


class IngestPrResponse(IngestCommitResponse):
    # `True` si la PR nació con las reviews copiadas de su commit idéntico (mismo SHA y diff, ya
    # revisado por todos los agentes): no se arranca ninguna revisión nueva.
    reused: bool = False


class ProjectResponse(BaseModel):
    id: UUID
    slug: str
    # Carpeta local desde la que se dio de alta; `null` si el proyecto no tiene una.
    path: str | None
    hooks_installed: bool
    github: bool

    @classmethod
    def from_domain(cls, project: Project) -> ProjectResponse:
        return cls(
            id=project.id,
            slug=project.slug,
            path=project.path,
            hooks_installed=project.hooks_installed,
            github=project.github,
        )


class AddProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Ruta absoluta de la raíz de un repo git; la validación a fondo la hace el caso de uso.
    path: str = Field(min_length=1, max_length=4096, pattern=NO_NUL)


class SyncPrsResponse(BaseModel):
    synced: int
    created: int


class DiffFileResponse(BaseModel):
    path: str
    additions: int
    deletions: int


class DiffSummaryResponse(BaseModel):
    """Archivos y líneas del diff, calculados al ingerir. `files` se acota a 200 entradas;
    `files_changed` es el recuento real."""

    files_changed: int
    additions: int
    deletions: int
    files: list[DiffFileResponse]

    @classmethod
    def from_domain(cls, summary: DiffSummary) -> DiffSummaryResponse:
        return cls(
            files_changed=summary.files_changed,
            additions=summary.additions,
            deletions=summary.deletions,
            files=[
                DiffFileResponse(path=f.path, additions=f.additions, deletions=f.deletions)
                for f in summary.files
            ],
        )


class RevertedByResponse(BaseModel):
    """El commit que revierte a otro (`git revert`): lo mínimo para nombrarlo y enlazarlo."""

    id: UUID
    head_sha: str

    @classmethod
    def from_domain(cls, ref: RevertRef) -> RevertedByResponse:
        return cls(id=ref.id, head_sha=ref.head_sha)


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
    diff_summary: DiffSummaryResponse
    # Diagnóstico: sigue `pending`/`running` más allá de `STALE_AFTER_SECONDS`.
    stale: bool
    # `discarded`: el commit ya no es alcanzable desde ninguna referencia del repositorio local
    # (`reset`, `amend`, `rebase`...); `reverted`: otro commit lo invierte con `git revert`. Una PR
    # siempre es `active`. No cambia `review_status` ni borra nada.
    commit_state: CommitState = CommitState.ACTIVE
    # El commit que lo revierte, si `commit_state` es `reverted` y se conoce.
    reverted_by: RevertedByResponse | None = None

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
            diff_summary=DiffSummaryResponse.from_domain(change.diff_summary),
            stale=change.stale,
            commit_state=change.commit_state,
            reverted_by=(
                RevertedByResponse.from_domain(change.reverted_by) if change.reverted_by else None
            ),
        )


class ReviewBriefResponse(BaseModel):
    """Review reducida del listado: sin resumen, hallazgos, error ni salida cruda. El detalle
    completo se pide con `GET /changes/{id}`."""

    agent: str
    status: ReviewStatus
    score: int | None
    duration_ms: int | None
    run: int
    # Change del que se copió la review (PR con las de su commit idéntico); `null` si es propia.
    reused_from: UUID | None = None

    @classmethod
    def from_domain(cls, brief: ReviewBrief) -> ReviewBriefResponse:
        return cls(
            agent=brief.agent,
            status=brief.status,
            score=brief.score,
            duration_ms=brief.duration_ms,
            run=brief.run,
            reused_from=brief.reused_from,
        )


class ChangeListItemResponse(ChangeSummaryResponse):
    """Elemento del canal: el resumen del change más las reviews ligeras de su run actual."""

    reviews: list[ReviewBriefResponse]

    @classmethod
    def from_summary(cls, change: ChangeSummary) -> ChangeListItemResponse:
        base = ChangeSummaryResponse.from_summary(change)
        return cls(
            **base.model_dump(),
            reviews=[ReviewBriefResponse.from_domain(r) for r in change.reviews],
        )


class ChangePageResponse(BaseModel):
    items: list[ChangeListItemResponse]
    next_cursor: str | None = None

    @classmethod
    def from_page(cls, page: ChangePage, next_cursor: str | None) -> ChangePageResponse:
        return cls(
            items=[ChangeListItemResponse.from_summary(c) for c in page.items],
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
    # Change del que se copió la review (PR con las de su commit idéntico); `null` si es propia.
    reused_from: UUID | None = None

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
            reused_from=review.reused_from_change_id,
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
            diff_summary=DiffSummaryResponse.from_domain(change.diff_summary),
            stale=detail.stale,
            commit_state=detail.commit_state,
            reverted_by=(
                RevertedByResponse.from_domain(detail.reverted_by) if detail.reverted_by else None
            ),
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


class ChangeEventResponse(BaseModel):
    """Evento de la línea de tiempo con el payload reducido: solo `agent` y `review_id`, nunca la
    salida cruda ni el texto de un error."""

    id: int
    type: str
    created_at: datetime
    agent: str | None
    review_id: UUID | None

    @classmethod
    def from_domain(cls, event: ChangeEvent) -> ChangeEventResponse:
        return cls(
            id=event.id,
            type=event.type,
            created_at=event.created_at,
            agent=event.agent,
            review_id=event.review_id,
        )


class RawOutputResponse(BaseModel):
    review_id: UUID
    raw_output: str

    @classmethod
    def from_domain(cls, output: RawOutput) -> RawOutputResponse:
        return cls(review_id=output.review_id, raw_output=output.raw_output)


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
    # Agentes configurados (`AGENT_NAMES`); la UI los usa en vez de suponer «Claude y Codex».
    agent_names: list[str]


class ErrorResponse(BaseModel):
    detail: str
