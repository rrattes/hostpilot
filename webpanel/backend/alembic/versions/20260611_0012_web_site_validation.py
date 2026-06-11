"""web site validation setting

Revision ID: 20260611_0012
Revises: 20260611_0011
Create Date: 2026-06-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260611_0012"
down_revision: str | None = "20260611_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SETTING = ("web.sites.allowed_base_path", "/var/www/hostpilot-sites", False)


def upgrade() -> None:
    connection = op.get_bind()
    exists = connection.execute(
        sa.text("select 1 from settings where key = :key"),
        {"key": SETTING[0]},
    ).first()
    if exists is None:
        settings_table = sa.table(
            "settings",
            sa.column("key", sa.String),
            sa.column("value", sa.Text),
            sa.column("is_sensitive", sa.Boolean),
        )
        op.bulk_insert(
            settings_table,
            [{"key": SETTING[0], "value": SETTING[1], "is_sensitive": SETTING[2]}],
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("delete from settings where key = :key"),
        {"key": SETTING[0]},
    )
