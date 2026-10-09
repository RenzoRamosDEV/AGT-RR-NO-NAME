from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

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
    ) -> Change:
        if not head_sha:
            raise ValueError("head_sha no puede estar vacío")
        _validate_identifier("head_sha", head_sha, MAX_HEAD_SHA)
        _validate_identifier("ref", ref, MAX_REF)
        _validate_identifier("url", url, MAX_URL)
        return cls(
            id=uuid4(),
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
        )
