"""changes.discarded_at y reverts_sha: commits deshechos y revertidos

Revision ID: h8e6f0c4d237
Revises: g7d5e9b3c126
Create Date: 2026-10-10 17:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h8e6f0c4d237"
down_revision: str | None = "g7d5e9b3c126"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Ambas columnas son opcionales y los changes existentes quedan sin marca (`active`): el
    # historial se conserva tal cual y el barrido de alcanzabilidad marcará lo que proceda.
    op.add_column("changes", sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True))
    # El SHA que revierte un commit de `git revert`. Es un dato del propio commit (no un puntero
    # en el original), así que no importa en qué orden lleguen ni qué pase después con un `amend`.
    op.add_column("changes", sa.Column("reverts_sha", sa.String(length=64), nullable=True))
    # «¿Hay un revert vivo de este commit?»: el canal lo pregunta por cada fila. Solo los commits de
    # revert (muy pocos) entran en este índice parcial.
    op.create_index(
        "ix_changes_project_reverts_sha",
        "changes",
        ["project_id", "reverts_sha"],
        postgresql_where=sa.text("reverts_sha IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_changes_project_reverts_sha", table_name="changes")
    op.drop_column("changes", "reverts_sha")
    op.drop_column("changes", "discarded_at")
