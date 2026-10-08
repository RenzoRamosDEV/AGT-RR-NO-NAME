"""reviews table

Revision ID: 1f9758d504b6
Revises: 5aed9a6421bc
Create Date: 2026-10-08 23:23:06.057073

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1f9758d504b6"
down_revision: str | None = "5aed9a6421bc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "change_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("changes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent", sa.String(length=50), nullable=False),
        sa.Column("run", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("findings", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("change_id", "agent", "run", name="uq_reviews_natural_key"),
    )
    op.create_index("ix_reviews_change_id", "reviews", ["change_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reviews_change_id", table_name="reviews")
    op.drop_table("reviews")
