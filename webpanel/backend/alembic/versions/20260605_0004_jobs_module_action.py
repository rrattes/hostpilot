"""jobs module action fields

Revision ID: 20260605_0004
Revises: 20260605_0003
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0004"
down_revision: str | None = "20260605_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("module", sa.String(length=80), nullable=False, server_default="core"),
    )
    op.add_column(
        "jobs",
        sa.Column("action", sa.String(length=160), nullable=False, server_default="mock"),
    )
    op.create_index("ix_jobs_module", "jobs", ["module"])
    op.create_index("ix_jobs_action", "jobs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_jobs_action", table_name="jobs")
    op.drop_index("ix_jobs_module", table_name="jobs")
    op.drop_column("jobs", "action")
    op.drop_column("jobs", "module")
