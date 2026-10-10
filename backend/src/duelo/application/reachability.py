"""Barrido de alcanzabilidad: marca los commits que ya no están en el repositorio local.

Git no avisa cuando un commit se pierde (no hay hook para `reset` ni para `--amend`), así que de
vez en cuando se pregunta qué commits son alcanzables y se marcan como «deshechos» los changes que
ya no lo son (y se desmarcan los que vuelven). No borra ni cambia nada más: el change y sus reviews
quedan como estaban."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from duelo.application.ports import (
    CommitMarks,
    HistoryUnavailable,
    ProjectCatalog,
    RepositoryHistory,
)
from duelo.domain.commit_state import decide_reachability
from duelo.domain.project import Project

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SweepResult:
    discarded: int
    restored: int


async def sweep_project(
    history: RepositoryHistory,
    marks: CommitMarks,
    project: Project,
    *,
    window: int,
    now: datetime,
) -> SweepResult:
    """Barre un proyecto con carpeta local. Lanza `HistoryUnavailable` (sin marcar nada) si git no
    se puede consultar.

    Los changes se leen ANTES de preguntar a git: un commit ingerido entre ambos pasos no está en
    la lista y no se evalúa, en lugar de parecer «deshecho» por no estar en una foto anterior."""
    if project.path is None:
        return SweepResult(0, 0)
    tracked = await marks.tracked_commits(project.id)
    if not tracked:
        return SweepResult(0, 0)
    reachability = await history.reachable(project.path, limit=window)
    decision = decide_reachability(tracked, reachability)

    discard = list(decision.discard)
    if decision.confirm_individually and discard:
        # Con la ventana llena, un commit antiguo ingerido tarde (recuperado por `pre-push`) puede
        # ser alcanzable aunque no esté en ella: se comprueba uno a uno solo a los candidatos.
        confirmed = []
        for commit in discard:
            if not await history.contains(project.path, commit.head_sha):
                confirmed.append(commit)
        discard = confirmed

    if not discard and not decision.restore:
        return SweepResult(0, 0)
    discarded, restored = await marks.apply(
        project.id,
        discard=[c.id for c in discard],
        restore=[c.id for c in decision.restore],
        at=now,
    )
    return SweepResult(discarded=discarded, restored=restored)


async def sweep_all(
    catalog: ProjectCatalog,
    history: RepositoryHistory,
    marks: CommitMarks,
    *,
    window: int,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, SweepResult]:
    """Barre todos los proyectos locales. Uno que falla (carpeta movida, git sin respuesta) se
    registra y no marca nada; los demás siguen."""
    results: dict[str, SweepResult] = {}
    for project in await catalog.list_local():
        try:
            results[project.slug] = await sweep_project(
                history, marks, project, window=window, now=clock()
            )
        except HistoryUnavailable:
            logger.warning("No se pudo consultar el historial de %s", project.slug, exc_info=True)
        except Exception:
            logger.warning("Falló el barrido de %s", project.slug, exc_info=True)
    return results
