from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from duelo.application.read_models import StoredEvent
from duelo.domain.events import ChangeCreated, ReviewCompleted, ReviewFailed

Event = ChangeCreated | ReviewCompleted | ReviewFailed


class FakeEventLog:
    """Outbox en memoria compartido por los repositorios fake: guarda cada evento con su id
    autoincremental, igual que la tabla `events`."""

    def __init__(self) -> None:
        self._rows: list[tuple[UUID, StoredEvent]] = []

    def append(self, event: Event, *, project_id: UUID) -> None:
        stored = StoredEvent(
            id=len(self._rows) + 1,
            type=event.type,
            payload=event.to_payload(),
            created_at=datetime.now(UTC),
        )
        self._rows.append((project_id, stored))

    def append_raw(self, *, project_id: UUID, type: str, payload: dict[str, object]) -> None:
        """Un evento arbitrario (tipos desconocidos, campos de más) para probar la lista blanca."""
        stored = StoredEvent(
            id=len(self._rows) + 1, type=type, payload=payload, created_at=datetime.now(UTC)
        )
        self._rows.append((project_id, stored))


class FakeChangeEventRepository:
    def __init__(self, log: FakeEventLog) -> None:
        self._log = log

    async def list_for_change(self, project_id: UUID, change_id: UUID) -> list[StoredEvent]:
        return [
            stored
            for owner, stored in self._log._rows
            if owner == project_id and stored.payload.get("change_id") == str(change_id)
        ]
