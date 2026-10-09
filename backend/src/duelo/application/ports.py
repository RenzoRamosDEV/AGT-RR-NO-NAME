from __future__ import annotations

from typing import Protocol
from uuid import UUID

from duelo.application.read_models import AgentStats, ChangeCursor, ChangeSummary
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.project import Project
from duelo.domain.review import Review, ReviewResult


class ChangeRepository(Protocol):
    async def add(self, change: Change, event: ChangeCreated) -> Change:
        """Persiste `change` y `event` en una única transacción.

        Si ya existía un `Change` con la misma identidad natural
        (project_id, kind, head_sha), lo devuelve sin crear un segundo evento.
        """
        ...

    async def get(self, change_id: UUID) -> Change | None:
        """Devuelve el `Change` con ese id, o `None` si no existe."""
        ...

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        kind: ChangeKind | None,
        limit: int,
        after: ChangeCursor | None,
    ) -> list[ChangeSummary]:
        """Devuelve a lo sumo `limit` changes del proyecto, del más reciente al más antiguo
        (orden por (created_at, id) descendente), posteriores a `after` si se indica y
        filtrados por `kind` si se indica. No incluye el diff."""
        ...


class ReviewAgent(Protocol):
    name: str

    async def review(self, change: Change) -> ReviewResult:
        """Revisa `change` y devuelve su resultado. Puede lanzar una excepción si
        la review falla - el caller decide cómo registrar ese fallo."""
        ...


class ReviewRepository(Protocol):
    async def add(self, review: Review, event: ReviewCompleted | ReviewFailed) -> Review:
        """Persiste `review` y `event` en una única transacción.

        Si ya existía una `Review` con la misma identidad natural
        (change_id, agent, run), la devuelve sin crear un segundo evento.
        """
        ...

    async def list_for_change(self, change_id: UUID) -> list[Review]:
        """Devuelve las reviews del change (completadas y fallidas) por fecha de creación."""
        ...

    async def agent_stats(self) -> list[AgentStats]:
        """Métricas agregadas por agente, ordenadas por nombre. Las medias ignoran los
        valores nulos y son `None` si no hay ninguno."""
        ...


class ProjectRepository(Protocol):
    async def get_by_slug(self, slug: str) -> Project | None:
        """Devuelve el proyecto con ese slug, o `None` si no existe."""
        ...

    async def list_all(self) -> list[Project]:
        """Devuelve todos los proyectos ordenados por slug."""
        ...


class ReviewStartError(Exception):
    """El orquestador no pudo arrancar la review (p. ej. Temporal caído)."""


class ReviewStarter(Protocol):
    async def start(self, change: Change) -> None:
        """Arranca la review de `change`. Idempotente: si ya estaba arrancada (o terminó)
        para ese change, no hace nada. Lanza `ReviewStartError` si no se pudo arrancar."""
        ...
