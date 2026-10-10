from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from duelo.domain.diff import EMPTY_DIFF_SUMMARY, DiffSummary, summarize_diff

# Límites de negocio; coinciden con las columnas de `changes` (un test lo garantiza).
MAX_HEAD_SHA = 64
MAX_REF = 255
MAX_URL = 1000
MAX_TITLE = 500
MAX_AUTHOR = 255


def _validate_identifier(name: str, value: str, limit: int) -> None:
    if "\x00" in value:
        raise ValueError(f"{name} no puede contener el carácter NUL")
    if len(value) > limit:
        raise ValueError(f"{name} no puede superar {limit} caracteres (recibidos {len(value)})")


class ChangeKind(StrEnum):
    COMMIT = "commit"
    PR = "pr"


class ChangeStatus(StrEnum):
    PENDING = "pending"


@dataclass(frozen=True, slots=True)
class Change:
    id: UUID
    project_id: UUID
    kind: ChangeKind
    ref: str
    head_sha: str
    title: str
    author: str
    url: str
    diff: str
    diff_truncated: bool
    status: ChangeStatus
    run: int
    created_at: datetime
    # Cuándo empezó el `run` actual: la creación para el primero y el reintento para los demás.
    # `stale` se mide desde aquí.
    run_started_at: datetime
    diff_summary: DiffSummary = EMPTY_DIFF_SUMMARY
    # Solo los commits: cuándo dejó de ser alcanzable desde el repositorio local (`reset`, `amend`,
    # `rebase`...), o `None` si lo sigue siendo. El estado se deduce con `commit_state_of`.
    discarded_at: datetime | None = None
    # Solo los commits: el SHA que este commit revierte (`This reverts commit <sha>` de un
    # `git revert`), o `None`. Un commit está «revertido» mientras exista un commit de revert que
    # sigue en la rama y apunta a su SHA: así no importa el orden de llegada ni los `amend`.
    reverts_sha: str | None = None

    @classmethod
    def new(
        cls,
        *,
        project_id: UUID,
        kind: ChangeKind,
        ref: str,
        head_sha: str,
        title: str,
        author: str,
        url: str,
        diff: str,
        diff_truncated: bool,
        created_at: datetime,
        id: UUID | None = None,
        reverts_sha: str | None = None,
    ) -> Change:
        if not head_sha:
            raise ValueError("head_sha no puede estar vacío")
        _validate_identifier("head_sha", head_sha, MAX_HEAD_SHA)
        _validate_identifier("ref", ref, MAX_REF)
        _validate_identifier("url", url, MAX_URL)
        return cls(
            id=id if id is not None else uuid4(),
            project_id=project_id,
            kind=kind,
            ref=ref,
            head_sha=head_sha,
            title=title[:MAX_TITLE],
            author=author[:MAX_AUTHOR],
            url=url,
            diff=diff,
            diff_truncated=diff_truncated,
            status=ChangeStatus.PENDING,
            run=1,
            created_at=created_at,
            run_started_at=created_at,
            diff_summary=summarize_diff(diff),
            reverts_sha=reverts_sha if kind is ChangeKind.COMMIT else None,
        )
