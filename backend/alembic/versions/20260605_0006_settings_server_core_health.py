"""settings server core health

Revision ID: 20260605_0006
Revises: 20260605_0005
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0006"
down_revision: str | None = "20260605_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SETTINGS = [
    ("core.product_name", "HostPilot", False),
    ("core.timezone", "UTC", False),
    ("core.audit_retention_days", "90", False),
]


def upgrade() -> None:
    op.add_column(
        "servers",
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
    )

    connection = op.get_bind()
    existing_settings = set(connection.execute(sa.text("select key from settings")).scalars().all())
    settings_table = sa.table(
        "settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
        sa.column("is_sensitive", sa.Boolean),
    )
    inserts = [
        {"key": key, "value": value, "is_sensitive": is_sensitive}
        for key, value, is_sensitive in SETTINGS
        if key not in existing_settings
    ]
    if inserts:
        op.bulk_insert(settings_table, inserts)

    connection.execute(
        sa.text(
            "update servers set description = :description where slug = :slug and description = ''"
        ),
        {"slug": "local", "description": "Local HostPilot server record."},
    )


def downgrade() -> None:
    op.drop_column("servers", "description")
