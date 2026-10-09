from __future__ import annotations

from dataclasses import dataclass

from duelo.application.ingest_change import ingest_change
from duelo.application.ports import ChangeRepository, ProjectRepository, ReviewStarter
from duelo.domain.change import Change, ChangeKind


class ProjectNotFound(Exception):
    def __init__(self, slug: str) -> None:
        super().__init__(f"Proyecto desconocido: {slug}")
        self.slug = slug


@dataclass(frozen=True)
class CommitSubmission:
    project: str
    ref: str
    head_sha: str
    title: str
    author: str
    url: str
    diff: str


async def ingest_commit(
    projects: ProjectRepository,
    changes: ChangeRepository,
    starter: ReviewStarter,
    submission: CommitSubmission,
    *,
    max_diff_chars: int,
) -> Change:
    """Persiste el commit y arranca su review. Ambos pasos son idempotentes, así que
    reintentar tras un fallo del starter es seguro: el `Change` ya está guardado."""
    project = await projects.get_by_slug(submission.project)
    if project is None:
        raise ProjectNotFound(submission.project)

    change = await ingest_change(
        changes,
        project_id=project.id,
        kind=ChangeKind.COMMIT,
        ref=submission.ref,
        head_sha=submission.head_sha,
        title=submission.title,
        author=submission.author,
        url=submission.url,
        diff=submission.diff[:max_diff_chars],
        diff_truncated=len(submission.diff) > max_diff_chars,
    )
    await starter.start(change)
    return change
