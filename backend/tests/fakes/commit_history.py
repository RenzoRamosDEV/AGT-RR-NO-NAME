"""Dobles de los puertos del barrido de alcanzabilidad: el historial de git y las marcas."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from duelo.application.ports import HistoryUnavailable
from duelo.domain.change import ChangeKind
from duelo.domain.commit_state import Reachability, TrackedCommit, normalize_sha
from duelo.domain.events import CommitDiscarded, CommitRestored
from tests.fakes.change_repository import FakeChangeRepository
from tests.fakes.event_log import FakeEventLog


class FakeRepositoryHistory:
    """Historial por carpeta, configurable: qué SHAs son alcanzables, si el conjunto sale truncado y
    qué carpetas fallan."""

    def __init__(self) -> None:
        self._reachable: dict[str, Reachability] = {}
        self._contained: dict[str, set[str]] = {}
        self._broken: set[str] = set()
        self.reachable_calls: list[tuple[str, int]] = []
        self.contains_calls: list[tuple[str, str]] = []

    def set_reachable(
        self,
        path: str,
        shas: Sequence[str],
        *,
        truncated: bool = False,
        oldest_at: datetime | None = None,
    ) -> None:
        self._reachable[path] = Reachability(
            shas=frozenset(normalize_sha(s) for s in shas), truncated=truncated, oldest_at=oldest_at
        )

    def set_contained(self, path: str, shas: Sequence[str]) -> None:
        """Los SHAs que la comprobación individual dará por alcanzables."""
        self._contained[path] = {normalize_sha(s) for s in shas}

    def break_repository(self, path: str) -> None:
        self._broken.add(path)

    async def reachable(self, path: str, *, limit: int) -> Reachability:
        self.reachable_calls.append((path, limit))
        if path in self._broken:
            raise HistoryUnavailable("repositorio no disponible")
        return self._reachable.get(path, Reachability(shas=frozenset(), truncated=False))

    async def contains(self, path: str, sha: str) -> bool:
        self.contains_calls.append((path, sha))
        if path in self._broken:
            raise HistoryUnavailable("repositorio no disponible")
        return normalize_sha(sha) in self._contained.get(path, set())


class FakeCommitMarks:
    """Marcas de deshecho sobre los changes del `FakeChangeRepository`, con sus eventos."""

    def __init__(self, changes: FakeChangeRepository, events: FakeEventLog | None = None) -> None:
        self._changes = changes
        self._events = events
        self.apply_calls = 0

    async def tracked_commits(self, project_id: UUID) -> list[TrackedCommit]:
        return [
            TrackedCommit(
                id=c.id,
                head_sha=c.head_sha,
                created_at=c.created_at,
                discarded=c.discarded_at is not None,
            )
            for c in self._changes._by_id.values()
            if c.project_id == project_id and c.kind is ChangeKind.COMMIT
        ]

    async def apply(
        self,
        project_id: UUID,
        *,
        discard: Sequence[UUID],
        restore: Sequence[UUID],
        at: datetime,
    ) -> tuple[int, int]:
        self.apply_calls += 1
        discarded = restored = 0
        for change_id in discard:
            change = self._changes._by_id[change_id]
            if change.discarded_at is None:
                self._changes.mark_discarded(change_id, at)
                discarded += 1
                self._emit(CommitDiscarded(change_id=change_id, project_id=project_id), project_id)
        for change_id in restore:
            change = self._changes._by_id[change_id]
            if change.discarded_at is not None:
                self._changes.mark_discarded(change_id, None)
                restored += 1
                self._emit(CommitRestored(change_id=change_id, project_id=project_id), project_id)
        return discarded, restored

    def _emit(self, event: CommitDiscarded | CommitRestored, project_id: UUID) -> None:
        if self._events is not None:
            self._events.append(event, project_id=project_id)
