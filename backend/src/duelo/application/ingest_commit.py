from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from duelo.application.ingest_change import ingest_change
from duelo.application.ports import ChangeRepository, ProjectRepository, ReviewStarter
from duelo.domain.change import Change, ChangeKind


class ProjectNotFound(Exception):
    def __init__(self, slug: str) -> None:
        super().__init__(f"Proyecto desconocido: {slug}")
        self.slug = slug


@dataclass(frozen=True)
class ChangeSubmission:
    """Lo que envía un cliente para un commit o un PR (el tipo lo fija el caso de uso)."""

    project: str
    ref: str
    head_sha: str
    title: str
    author: str
    url: str
    diff: str


CommitSubmission = ChangeSubmission


@dataclass(frozen=True)
class IngestResult:
    change: Change
    # `False` si el change ya existía (reingesta idempotente).
    created: bool


async def _ingest(
    kind: ChangeKind,
    projects: ProjectRepository,
    changes: ChangeRepository,
    starter: ReviewStarter,
    submission: ChangeSubmission,
    *,
    max_diff_chars: int,
) -> IngestResult:
    project = await projects.get_by_slug(submission.project)
    if project is None:
        raise ProjectNotFound(submission.project)

    candidate_id = uuid4()
    change = await ingest_change(
        changes,
        project_id=project.id,
        kind=kind,
        ref=submission.ref,
        head_sha=submission.head_sha,
        title=submission.title,
        author=submission.author,
        url=submission.url,
        diff=submission.diff[:max_diff_chars],
        diff_truncated=len(submission.diff) > max_diff_chars,
        change_id=candidate_id,
    )
    await starter.start(change)
    return IngestResult(change=change, created=change.id == candidate_id)


async def ingest_commit(
    projects: ProjectRepository,
    changes: ChangeRepository,
    starter: ReviewStarter,
    submission: ChangeSubmission,
    *,
    max_diff_chars: int,
) -> IngestResult:
    """Persiste el commit y arranca su review. Ambos pasos son idempotentes, así que
    reintentar tras un fallo del starter es seguro: el `Change` ya está guardado."""
    return await _ingest(
        ChangeKind.COMMIT, projects, changes, starter, submission, max_diff_chars=max_diff_chars
    )


async def ingest_pr(
    projects: ProjectRepository,
    changes: ChangeRepository,
    starter: ReviewStarter,
    submission: ChangeSubmission,
    *,
    max_diff_chars: int,
) -> IngestResult:
    """Igual que `ingest_commit` para un PR: la identidad es (proyecto, `pr`, head_sha)."""
    return await _ingest(
        ChangeKind.PR, projects, changes, starter, submission, max_diff_chars=max_diff_chars
    )
