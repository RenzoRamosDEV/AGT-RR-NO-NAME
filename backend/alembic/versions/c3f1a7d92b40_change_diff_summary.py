"""changes.diff_summary and events change index

Revision ID: c3f1a7d92b40
Revises: 1f9758d504b6
Create Date: 2026-10-09 22:00:00.000000

"""

import json
from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c3f1a7d92b40"
down_revision: str | None = "1f9758d504b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMPTY = '{"files_changed": 0, "additions": 0, "deletions": 0, "files": []}'
_BATCH = 100
_MAX_FILES = 200


def summarize_diff(diff: str) -> dict[str, object]:
    """Copia congelada de `duelo.domain.diff.summarize_diff`: una migración no debe depender
    del dominio vivo. Un test de integración comprueba que ambas coinciden."""
    files: list[dict[str, object]] = []
    in_hunk = False
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            rest = line.removeprefix("diff --git ")
            path = rest.rsplit(" b/", 1)[1] if " b/" in rest else rest
            files.append({"path": path, "additions": 0, "deletions": 0})
            in_hunk = False
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and files:
            if line.startswith("+"):
                files[-1]["additions"] = int(files[-1]["additions"]) + 1  # type: ignore[call-overload]
            elif line.startswith("-"):
                files[-1]["deletions"] = int(files[-1]["deletions"]) + 1  # type: ignore[call-overload]
    return {
        "files_changed": len(files),
        "additions": sum(int(f["additions"]) for f in files),  # type: ignore[call-overload]
        "deletions": sum(int(f["deletions"]) for f in files),  # type: ignore[call-overload]
        "files": files[:_MAX_FILES],
    }


def upgrade() -> None:
    op.add_column(
        "changes",
        sa.Column(
            "diff_summary",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text(f"'{_EMPTY}'::jsonb"),
        ),
    )
    _backfill()
    op.create_index(
        "ix_events_change_id", "events", [sa.text("(payload ->> 'change_id')")], unique=False
    )


def _backfill() -> None:
    """Rellena los changes existentes por lotes (keyset sobre `id`) para no cargar todos los
    diffs a la vez."""
    connection = op.get_bind()
    last: UUID | None = None
    while True:
        query = "SELECT id, diff FROM changes"
        params: dict[str, object] = {"limit": _BATCH}
        if last is not None:
            query += " WHERE id > :last"
            params["last"] = last
        rows = connection.execute(sa.text(query + " ORDER BY id LIMIT :limit"), params).all()
        if not rows:
            return
        for change_id, diff in rows:
            connection.execute(
                sa.text("UPDATE changes SET diff_summary = CAST(:summary AS jsonb) WHERE id = :id"),
                {"summary": json.dumps(summarize_diff(diff)), "id": change_id},
            )
        last = rows[-1][0]


def downgrade() -> None:
    op.drop_index("ix_events_change_id", table_name="events")
    op.drop_column("changes", "diff_summary")
