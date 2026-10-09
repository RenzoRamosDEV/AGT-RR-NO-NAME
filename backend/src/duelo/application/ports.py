from __future__ import annotations

from typing import Protocol
from uuid import UUID

from duelo.application.read_models import AgentStats, ChangeCursor, ChangeSummary, StoredEvent
from duelo.domain.change import Change, ChangeKind
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed
from duelo.domain.project import Project
from duelo.domain.review import Review, ReviewResult
from duelo.domain.review_status import ChangeReviewStatus


class ChangeRepository(Protocol):
    async def add(self, change: Change, event: ChangeCreated) -> Change:
        """Persiste `change` y `event` en una única transacción.

        Si ya existía un `Change` con la misma identidad natural
        (project_id, kind, head_sha), lo devuelve sin crear un segundo evento; su `id` es el del
        existente, distinto del de `change`, y así se distingue una reingesta.
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
        status: frozenset[ChangeReviewStatus] | None,
        q: str | None,
        expected_agents: int,
        limit: int,
        after: ChangeCursor | None,
    ) -> list[ChangeSummary]:
        """Devuelve a lo sumo `limit` changes del proyecto, del más reciente al más antiguo
        (orden por (created_at, id) descendente), posteriores a `after` si se indica. Filtra por
        `kind`, por `review_status` (cualquiera de los indicados, calculado frente a
        `expected_agents`) y por `q` (subcadena sin distinguir mayúsculas en título, autor, SHA o
        ref; sus comodines son texto literal) cuando se indican. No incluye el diff."""
        ...

    async def advance_run(self, change_id: UUID, *, from_run: int) -> Change | None:
        """Compare-and-swap: pasa `run` de `from_run` a `from_run + 1` y devuelve el change
        actualizado, o `None` si `run` ya no era `from_run` (otro reintento llegó antes) o el
        change no existe."""
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

    async def get(self, review_id: UUID) -> Review | None:
        """Devuelve la review con ese id (con su `raw_output`), o `None` si no existe."""
        ...

    async def agent_stats(self, *, project_id: UUID | None) -> list[AgentStats]:
        """Métricas agregadas por agente, ordenadas por nombre, de todas las reviews o solo de
        las de los changes de `project_id`. Las medias ignoran los valores nulos y son `None`
        si no hay ninguno."""
        ...


class ChangeEventRepository(Protocol):
    async def list_for_change(self, project_id: UUID, change_id: UUID) -> list[StoredEvent]:
        """Devuelve los eventos del outbox cuyo payload pertenece a `change_id`, en el orden en
        que se escribieron. El payload es crudo: filtrarlo es cosa del caso de uso."""
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
