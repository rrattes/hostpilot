"""web site readiness workflow

Revision ID: 20260611_0013
Revises: 20260611_0012
Create Date: 2026-06-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260611_0013"
down_revision: str | None = "20260611_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "web_sites",
        sa.Column("provisioning_status", sa.String(length=40), nullable=False, server_default="draft"),
    )
    op.create_index("ix_web_sites_provisioning_status", "web_sites", ["provisioning_status"])


def downgrade() -> None:
    op.drop_index("ix_web_sites_provisioning_status", table_name="web_sites")
    op.drop_column("web_sites", "provisioning_status")
