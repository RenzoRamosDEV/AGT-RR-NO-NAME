"""reviews.reused_from_change_id: la PR reutiliza las reviews de su commit idéntico

Revision ID: g7d5e9b3c126
Revises: f6c4d8a2b915
Create Date: 2026-10-10 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "g7d5e9b3c126"
down_revision: str | None = "f6c4d8a2b915"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column(
            "reused_from_change_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("changes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Borrar un change anula la marca en las reviews que copiaron de él: sin este índice parcial
    # cada borrado recorrería toda la tabla `reviews`. Las reviews propias (la inmensa mayoría)
    # no entran en él.
    op.create_index(
        "ix_reviews_reused_from_change_id",
        "reviews",
        ["reused_from_change_id"],
        postgresql_where=sa.text("reused_from_change_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_reviews_reused_from_change_id", table_name="reviews")
    op.drop_column("reviews", "reused_from_change_id")
