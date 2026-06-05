"""module registry state

Revision ID: 20260605_0005
Revises: 20260605_0004
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0005"
down_revision: str | None = "20260605_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MODULES = [
    ("core", "Core", "enabled"),
    ("web", "Web", "locked"),
    ("sites", "Sites", "locked"),
    ("nginx", "Nginx", "locked"),
    ("ssl", "SSL", "locked"),
    ("logs", "Logs", "locked"),
    ("services", "Services", "locked"),
    ("updates", "Updates", "locked"),
    ("backups", "Backups", "locked"),
    ("php-runtime", "PHP Runtime", "locked"),
    ("server-system", "Server & System", "locked"),
    ("remote-access", "Remote Access", "locked"),
    ("docker", "Docker", "locked"),
    ("kvm", "KVM", "locked"),
]


def upgrade() -> None:
    op.add_column(
        "modules",
        sa.Column("state", sa.String(length=40), nullable=False, server_default="locked"),
    )
    op.create_index("ix_modules_state", "modules", ["state"])

    connection = op.get_bind()
    existing = set(connection.execute(sa.text("select slug from modules")).scalars().all())
    modules_table = sa.table(
        "modules",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("version", sa.String),
        sa.column("state", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("locked", sa.Boolean),
        sa.column("installed", sa.Boolean),
    )

    inserts = []
    for slug, name, state in MODULES:
        flags = _flags_for_state(state)
        if slug not in existing:
            inserts.append(
                {
                    "slug": slug,
                    "name": name,
                    "version": "0.1.0",
                    "state": state,
                    **flags,
                }
            )
        else:
            connection.execute(
                sa.text(
                    "update modules set name = :name, state = :state, enabled = :enabled, "
                    "locked = :locked, installed = :installed where slug = :slug"
                ),
                {"slug": slug, "name": name, "state": state, **flags},
            )

    if inserts:
        op.bulk_insert(modules_table, inserts)

    connection.execute(sa.text("delete from modules where slug in ('docker-containers', 'kvm-virtualization')"))


def downgrade() -> None:
    op.drop_index("ix_modules_state", table_name="modules")
    op.drop_column("modules", "state")


def _flags_for_state(state: str) -> dict[str, bool]:
    return {
        "enabled": state == "enabled",
        "locked": state == "locked",
        "installed": state in {"installed", "enabled"},
    }
