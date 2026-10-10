from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import uuid4

from duelo.application.ingest_change import ingest_change
from duelo.application.ports import ChangeRepository, ProjectRepository, ReviewStarter
from duelo.domain.change import Change, ChangeKind
from duelo.domain.commit_state import parse_reverted_sha


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
    # Cuerpo del mensaje del commit (lo que sigue a la primera línea): solo se lee para detectar
    # `This reverts commit <sha>`; no se guarda. Vacío si el cliente no lo envía.
    body: str = ""


CommitSubmission = ChangeSubmission


@dataclass(frozen=True)
class IngestResult:
    change: Change
    # `False` si el change ya existía (reingesta idempotente).
    created: bool
    # `True` si es una PR con las reviews copiadas de su commit idéntico (su run 1): no se
    # revisa de nuevo, así que no tiene workflow.
    reused: bool = False


def _reverted_sha(kind: ChangeKind, submission: ChangeSubmission) -> str | None:
    """El SHA que revierte un commit de `git revert` (`This reverts commit <sha>` en su mensaje),
    o `None`. Un commit que se nombrase a sí mismo no revierte nada, y una PR nunca revierte."""
    if kind is not ChangeKind.COMMIT:
        return None
    reverted = parse_reverted_sha(submission.title, submission.body)
    return None if reverted == submission.head_sha.lower() else reverted


async def _ingest(
    kind: ChangeKind,
    projects: ProjectRepository,
    changes: ChangeRepository,
    starter: ReviewStarter,
    submission: ChangeSubmission,
    *,
    max_diff_chars: int,
    agent_names: Sequence[str] = (),
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
        agent_names=agent_names,
        reverts_sha=_reverted_sha(kind, submission),
    )
    # Con las reviews ya copiadas no hay nada que revisar: arrancar el workflow gastaría la
    # suscripción de los agentes. Tras un reintento (`run` > 1) vuelve a ser una PR normal.
    reused = (
        kind is ChangeKind.PR and change.run == 1 and await changes.has_reused_reviews(change.id)
    )
    if not reused:
        await starter.start(change)
    return IngestResult(change=change, created=change.id == candidate_id, reused=reused)


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
    agent_names: Sequence[str] = (),
) -> IngestResult:
    """Igual que `ingest_commit` para un PR: la identidad es (proyecto, `pr`, head_sha).

    Si el commit con ese mismo SHA y diff ya lo revisaron todos los `agent_names`, la PR nace con
    esas reviews y no arranca workflow (ver `reviews_to_reuse`)."""
    return await _ingest(
        ChangeKind.PR,
        projects,
        changes,
        starter,
        submission,
        max_diff_chars=max_diff_chars,
        agent_names=agent_names,
    )
