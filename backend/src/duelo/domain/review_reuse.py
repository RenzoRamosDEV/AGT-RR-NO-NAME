"""Cuándo una PR puede aprovechar las reviews de su commit en vez de volver a pedirlas.

Un commit y una PR cuyo último commit tiene el mismo SHA son dos `Change` distintos, pero si la PR
tiene un solo commit su diff es el mismo y revisarlo otra vez gasta, sin aportar nada, la
suscripción de cada agente. La decisión es pura: sin E/S, solo reglas."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime

from duelo.domain.change import Change, ChangeKind
from duelo.domain.review import Review, ReviewStatus


def reviews_to_reuse(
    change: Change,
    source: Change | None,
    source_reviews: Iterable[Review],
    *,
    agent_names: Sequence[str],
    now: datetime,
) -> tuple[Review, ...]:
    """Copias de las reviews de `source` para `change`, o una tupla vacía si no procede.

    Procede solo si `change` es una PR y `source` un commit del mismo proyecto con el mismo SHA y
    exactamente el mismo diff (una PR de varios commits tiene otro), y si `source` tiene una review
    completada de su `run` actual de cada agente de `agent_names`. Si falta uno, o falló, la PR se
    revisa con normalidad: reutilizar solo una parte dejaría la PR en `running` sin workflow.
    El diff se compara tal cual; uno con NUL (que el repositorio sanea al guardar) no coincide y
    se revisa con normalidad, que es el lado seguro.

    El estado de un change espera `len(agent_names)` reviews, así que la lista se usa tal cual y no
    como un conjunto: con un nombre repetido (que la configuración ya rechaza) una sola review
    «satisfaría» a todos, la PR copiaría menos reviews de las esperadas y quedaría `running` sin
    workflow. Con repetidos no se reutiliza nada."""
    if not agent_names or source is None or len(set(agent_names)) != len(agent_names):
        return ()
    if change.kind is not ChangeKind.PR or source.kind is not ChangeKind.COMMIT:
        return ()
    if source.project_id != change.project_id or source.head_sha != change.head_sha:
        return ()
    if source.diff != change.diff or source.diff_truncated != change.diff_truncated:
        return ()

    by_agent: dict[str, Review] = {}
    for review in source_reviews:
        if review.run == source.run and review.status is ReviewStatus.COMPLETED:
            by_agent[review.agent] = review
    if any(name not in by_agent for name in agent_names):
        return ()
    return tuple(
        Review.reused_from(by_agent[name], change_id=change.id, created_at=now)
        for name in agent_names
    )
