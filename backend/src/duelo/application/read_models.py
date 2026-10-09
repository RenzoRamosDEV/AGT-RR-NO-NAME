"""Modelos de lectura (proyecciones para consultas). No son entidades de dominio: no tienen
invariantes y existen para no cargar datos que la consulta no necesita (p. ej. el diff)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from duelo.domain.change import Change, ChangeKind, ChangeStatus
from duelo.domain.review import Review


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
    run: int
    created_at: datetime


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


@dataclass(frozen=True, slots=True)
class AgentStats:
    agent: str
    total: int
    completed: int
    failed: int
    avg_duration_ms: float | None
    avg_score: float | None
