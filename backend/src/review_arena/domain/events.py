from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ChangeCreated:
    change_id: UUID
    project_id: UUID
    kind: str
    head_sha: str

    type: str = "change.created"

    def to_payload(self) -> dict[str, Any]:
        return {
            "change_id": str(self.change_id),
            "project_id": str(self.project_id),
            "kind": self.kind,
            "head_sha": self.head_sha,
        }
