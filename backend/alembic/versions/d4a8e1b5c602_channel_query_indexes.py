"""indexes for the filtered channel and the review counters

Revision ID: d4a8e1b5c602
Revises: c3f1a7d92b40
Create Date: 2026-10-09 23:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a8e1b5c602"
down_revision: str | None = "c3f1a7d92b40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # El canal ordena por (created_at, id): con `id` en el índice cubre también el desempate y
    # el cursor. El de `kind` sirve al filtro por tipo. Se crea cada nuevo antes de borrar el
    # que sustituye.
    op.create_index(
        "ix_changes_project_created_at_id", "changes", ["project_id", "created_at", "id"]
    )
    op.create_index(
        "ix_changes_project_kind_created_at_id",
        "changes",
        ["project_id", "kind", "created_at", "id"],
    )
    op.drop_index("ix_changes_project_created_at", table_name="changes")
    # Los contadores del canal son index-only sobre (change_id, run, status); el prefijo
    # change_id sigue sirviendo a las lecturas por change.
    op.create_index("ix_reviews_change_run_status", "reviews", ["change_id", "run", "status"])
    op.drop_index("ix_reviews_change_id", table_name="reviews")


def downgrade() -> None:
    op.create_index("ix_reviews_change_id", "reviews", ["change_id"])
    op.drop_index("ix_reviews_change_run_status", table_name="reviews")
    op.create_index("ix_changes_project_created_at", "changes", ["project_id", "created_at"])
    op.drop_index("ix_changes_project_kind_created_at_id", table_name="changes")
    op.drop_index("ix_changes_project_created_at_id", table_name="changes")
