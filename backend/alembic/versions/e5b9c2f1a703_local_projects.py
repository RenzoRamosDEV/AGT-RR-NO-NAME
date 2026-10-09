"""projects added from a local folder: path, hooks_installed and github

Revision ID: e5b9c2f1a703
Revises: d4a8e1b5c602
Create Date: 2026-10-10 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5b9c2f1a703"
down_revision: str | None = "d4a8e1b5c602"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("path", sa.String(length=4096), nullable=True))
    op.add_column(
        "projects",
        sa.Column("hooks_installed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "projects", sa.Column("github", sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.create_unique_constraint("uq_projects_path", "projects", ["path"])


def downgrade() -> None:
    op.drop_constraint("uq_projects_path", "projects", type_="unique")
    op.drop_column("projects", "github")
    op.drop_column("projects", "hooks_installed")
    op.drop_column("projects", "path")
