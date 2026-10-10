"""Modelos de lectura (proyecciones para consultas). No son entidades de dominio: no tienen
invariantes y existen para no cargar datos que la consulta no necesita (p. ej. el diff)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from duelo.domain.change import Change, ChangeKind, ChangeStatus
from duelo.domain.commit_state import CommitState
from duelo.domain.diff import DiffSummary
from duelo.domain.review import Review, ReviewStatus
from duelo.domain.review_status import ChangeReviewStatus, FindingsSummary


@dataclass(frozen=True, slots=True)
class ReviewBrief:
    """Lo mínimo de una review para pintar el canal: sin resumen, hallazgos, error ni salida
    cruda, que se piden con el detalle del change."""

    agent: str
    status: ReviewStatus
    score: int | None
    duration_ms: int | None
    run: int
    # Change del que se copió la review (PR con las de su commit idéntico), o `None` si es propia.
    reused_from: UUID | None = None


@dataclass(frozen=True, slots=True)
class RevertRef:
    """El commit que revierte a otro: lo mínimo para enlazarlo y nombrarlo."""

    id: UUID
    head_sha: str


@dataclass(frozen=True, slots=True)
class ChangeSummary:
    """Un `Change` sin su diff, para listados."""

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
    run_started_at: datetime
    diff_summary: DiffSummary
    # Lo calcula el caso de uso con su reloj; el repositorio no lo conoce.
    stale: bool = False
    # Solo las del `run` actual, por agente.
    reviews: tuple[ReviewBrief, ...] = ()
    # Un commit puede estar deshecho o revertido; una PR siempre es `active`. No cambia
    # `review_status` ni conserva más que la marca: el change y sus reviews siguen intactos.
    commit_state: CommitState = CommitState.ACTIVE
    reverted_by: RevertRef | None = None


@dataclass(frozen=True, slots=True)
class ChangeCursor:
    """Posición en el canal: los changes se ordenan por (created_at, id) descendente."""

    created_at: datetime
    id: UUID


@dataclass(frozen=True, slots=True)
class ChangePage:
    items: tuple[ChangeSummary, ...]
    next_cursor: ChangeCursor | None


@dataclass(frozen=True, slots=True)
class ChangeDetail:
    change: Change
    reviews: tuple[Review, ...]
    review_status: ChangeReviewStatus
    findings_summary: FindingsSummary
    stale: bool = False
    commit_state: CommitState = CommitState.ACTIVE
    reverted_by: RevertRef | None = None


@dataclass(frozen=True, slots=True)
class AgentStats:
    agent: str
    total: int
    completed: int
    failed: int
    avg_duration_ms: float | None
    avg_score: float | None


@dataclass(frozen=True, slots=True)
class StoredEvent:
    """Una fila del outbox tal como está guardada: `payload` es crudo y NO se expone tal cual."""

    id: int
    type: str
    payload: Mapping[str, object]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ChangeEvent:
    """Evento de un change con el payload reducido que la API puede mostrar."""

    id: int
    type: str
    created_at: datetime
    agent: str | None
    review_id: UUID | None


@dataclass(frozen=True, slots=True)
class RawOutput:
    review_id: UUID
    raw_output: str
