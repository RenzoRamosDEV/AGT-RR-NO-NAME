"""changes.run_started_at: inicio del run actual, para medir stale

Revision ID: f6c4d8a2b915
Revises: e5b9c2f1a703
Create Date: 2026-10-10 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6c4d8a2b915"
down_revision: str | None = "e5b9c2f1a703"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "changes",
        sa.Column(
            "run_started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Lo único que se sabe de los changes anteriores es cuándo se crearon: un change reintentado
    # antes de esta migración pierde la precisión del reintento.
    op.execute("UPDATE changes SET run_started_at = created_at")


def downgrade() -> None:
    op.drop_column("changes", "run_started_at")
