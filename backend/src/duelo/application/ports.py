from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from duelo.application.read_models import (
    AgentStats,
    ChangeCursor,
    ChangeSummary,
    RevertRef,
    StoredEvent,
)
from duelo.domain.change import Change, ChangeKind
from duelo.domain.commit_state import Reachability, TrackedCommit
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed, ReviewReused
from duelo.domain.project import Project
from duelo.domain.review import Review, ReviewResult
from duelo.domain.review_status import ChangeReviewStatus


@dataclass(frozen=True, slots=True)
class CommitWithReviews:
    """Un commit y las reviews de su `run` actual: lo que una PR idéntica puede aprovechar."""

    change: Change
    reviews: tuple[Review, ...]


class ChangeRepository(Protocol):
    async def add(
        self,
        change: Change,
        event: ChangeCreated,
        reused: Sequence[tuple[Review, ReviewReused]] = (),
    ) -> Change:
        """Persiste `change`, `event` y, en la MISMA transacción, las reviews `reused` (cada una
        con su evento). Si `change` es un commit que revierte a otro que ya existe en el proyecto
        (`reverts_sha`), añade también el evento `commit.reverted` del original.

        Si ya existía un `Change` con la misma identidad natural
        (project_id, kind, head_sha), lo devuelve sin crear un segundo evento ni copiar reviews; su
        `id` es el del existente, distinto del de `change`, y así se distingue una reingesta.
        Una review que ya existiera (mismo change, agente y run) no se duplica ni repite su evento.
        """
        ...

    async def find_commit_with_reviews(
        self, project_id: UUID, head_sha: str
    ) -> CommitWithReviews | None:
        """El change de tipo `commit` de ese proyecto y SHA con las reviews de su `run` actual, o
        `None` si no existe."""
        ...

    async def has_reused_reviews(self, change_id: UUID) -> bool:
        """`True` si el change tiene alguna review de su `run` 1 copiada de otro change."""
        ...

    async def get(self, change_id: UUID) -> Change | None:
        """Devuelve el `Change` con ese id, o `None` si no existe."""
        ...

    async def live_reverter(self, project_id: UUID, head_sha: str) -> RevertRef | None:
        """El commit de revert más reciente que sigue en la rama (no deshecho) y apunta a
        `head_sha` (`Change.reverts_sha`) en ese proyecto, o `None` si no hay ninguno.

        Un revert que se deshace (`reset`, `amend`) deja de contar: el original vuelve a estar
        activo. Y como el dato vive en el commit de revert, no importa el orden de llegada."""
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

    async def advance_run(
        self, change_id: UUID, *, from_run: int, started_at: datetime
    ) -> Change | None:
        """Compare-and-swap: pasa `run` de `from_run` a `from_run + 1`, guarda `started_at` como
        inicio del nuevo `run` y devuelve el change actualizado, o `None` si `run` ya no era
        `from_run` (otro reintento llegó antes) o el change no existe."""
        ...


class ReviewAgent(Protocol):
    name: str

    async def review(self, change: Change) -> ReviewResult:
        """Revisa `change` y devuelve su resultado. Puede lanzar una excepción si
        la review falla - el caller decide cómo registrar ese fallo."""
        ...


class ProjectPaths(Protocol):
    async def path_of(self, project_id: UUID) -> str | None:
        """Devuelve la carpeta local del proyecto, o `None` si no existe o no tiene carpeta.

        Es lo único que un agente necesita saber de un proyecto, y le permite leer el repositorio
        sin que la ruta viaje por los DTOs de Temporal."""
        ...


class ProjectSlugs(Protocol):
    async def slug_of(self, project_id: UUID) -> str | None:
        """Devuelve el nombre (`owner/repo`) del proyecto, o `None` si no existe.

        Lo usa quien arranca un workflow para darle un nombre legible en la interfaz de Temporal."""
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
        """Devuelve los eventos del outbox cuyo payload pertenece a `change_id`, por orden
        cronológico (`created_at`; el `id` desempata). El payload es crudo: filtrarlo es cosa del
        caso de uso."""
        ...


class ProjectRepository(Protocol):
    async def get_by_slug(self, slug: str) -> Project | None:
        """Devuelve el proyecto con ese slug, o `None` si no existe."""
        ...

    async def list_all(self) -> list[Project]:
        """Devuelve todos los proyectos ordenados por slug."""
        ...


class ProjectAlreadyExists(Exception):
    """Ya hay un proyecto con ese slug o con esa carpeta."""


class InvalidRepository(Exception):
    """La ruta no es la raíz de un repositorio git utilizable (el mensaje es para el usuario)."""


class HookInstallError(Exception):
    """No se pudieron instalar o quitar los hooks (el mensaje es para el usuario)."""


class GithubUnavailable(Exception):
    """`gh` no está instalado, no ha iniciado sesión o no devolvió una respuesta válida."""


@dataclass(frozen=True, slots=True)
class RepoInfo:
    """Lo que hace falta saber de una carpeta para darla de alta como proyecto."""

    root: str
    # URL del remoto `origin`, o `None` si el repo no lo tiene.
    remote_url: str | None


@dataclass(frozen=True, slots=True)
class PullRequestInfo:
    number: int
    title: str
    author: str
    ref: str
    head_sha: str
    url: str
    diff: str


class GitRepository(Protocol):
    async def inspect(self, path: str) -> RepoInfo:
        """Comprueba que `path` es la raíz de un repo git (ruta absoluta, sin `..`, sin NUL, que
        no sea un enlace simbólico) y devuelve su raíz y su remoto `origin`. Lanza
        `InvalidRepository` en cualquier otro caso."""
        ...


class HookInstaller(Protocol):
    async def install(self, root: str, *, slug: str) -> None:
        """Instala los hooks `post-commit` y `pre-push` en el repo de `root` para el proyecto
        `slug`, sin tocar el contenido previo de esos hooks. Idempotente. Lanza `HookInstallError`
        sin haber modificado nada si no es posible (hook que no es de shell, `core.hooksPath`
        fuera del repo...)."""
        ...

    async def uninstall(self, root: str) -> None:
        """Quita los bloques de Duelo de los hooks de `root`, dejando intacto el resto. Si la
        carpeta ya no existe no hace nada."""
        ...


class GithubPrSource(Protocol):
    async def open_prs(self, root: str) -> list[PullRequestInfo]:
        """PRs abiertas del repo de `root` (con su diff). Lanza `GithubUnavailable` si no se
        pueden consultar."""
        ...


class HistoryUnavailable(Exception):
    """No se pudo consultar el historial del repositorio (carpeta movida o borrada, git ausente o
    sin respuesta...). Quien barre no debe marcar nada de ese proyecto."""


class RepositoryHistory(Protocol):
    async def reachable(self, path: str, *, limit: int) -> Reachability:
        """Los commits alcanzables desde todas las referencias y desde `HEAD` del repo de `path`
        (como mucho `limit`, los más recientes), con la fecha del más antiguo. Lanza
        `HistoryUnavailable` si no se puede consultar."""
        ...

    async def contains(self, path: str, sha: str) -> bool:
        """`True` si `sha` es alcanzable desde alguna referencia o desde `HEAD`. Un SHA que no sea
        hexadecimal nunca llega a git y da `False`. Lanza `HistoryUnavailable`."""
        ...


class CommitMarks(Protocol):
    async def tracked_commits(self, project_id: UUID) -> list[TrackedCommit]:
        """Los changes de tipo `commit` del proyecto, con lo que el barrido necesita saber."""
        ...

    async def apply(
        self,
        project_id: UUID,
        *,
        discard: Sequence[UUID],
        restore: Sequence[UUID],
        at: datetime,
    ) -> tuple[int, int]:
        """Marca como deshechos los changes de `discard` (con `discarded_at = at`) y desmarca los
        de `restore`, con su evento cada uno, en una transacción. Solo toca los que cambian de
        estado, así que es idempotente. Devuelve cuántos se marcaron y cuántos se desmarcaron."""
        ...


class ProjectCatalog(Protocol):
    async def add_local(self, project: Project) -> Project:
        """Registra un proyecto local. Lanza `ProjectAlreadyExists` si el slug o la carpeta ya
        están registrados."""
        ...

    async def remove(self, slug: str) -> Project | None:
        """Elimina el proyecto y, en cascada, sus changes, reviews y eventos. Devuelve el proyecto
        eliminado, o `None` si no existía."""
        ...

    async def list_local(self) -> list[Project]:
        """Proyectos dados de alta desde una carpeta, ordenados por slug."""
        ...


class ReviewStartError(Exception):
    """El orquestador no pudo arrancar la review (p. ej. Temporal caído)."""


class ReviewStarter(Protocol):
    async def start(self, change: Change) -> None:
        """Arranca la review de `change`. Idempotente: si ya estaba arrancada (o terminó)
        para ese change, no hace nada. Lanza `ReviewStartError` si no se pudo arrancar."""
        ...


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    # Segundos (enteros, >= 1) hasta que se libere cupo; 0 si la petición está permitida.
    retry_after_seconds: int


class RateLimiter(Protocol):
    async def hit(self, key: str) -> RateLimitDecision:
        """Registra una petición de `key` y dice si cabe en el cupo. Las rechazadas no cuentan
        contra el cupo (no prolongan el bloqueo)."""
        ...
