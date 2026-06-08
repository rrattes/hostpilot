"""core backups

Revision ID: 20260605_0009
Revises: 20260605_0008
Create Date: 2026-06-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0009"
down_revision: str | None = "20260605_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


timestamp = sa.text("CURRENT_TIMESTAMP")

PERMISSIONS = [
    ("core.backup.create", "Create Core backups."),
    ("core.backup.view", "View Core backup metadata."),
]


def upgrade() -> None:
    op.create_table(
        "core_backups",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
    )
    op.create_index("ix_core_backups_status", "core_backups", ["status"])

    connection = op.get_bind()
    existing_permissions = set(
        connection.execute(sa.text("select slug from permissions")).scalars().all()
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("slug", sa.String),
        sa.column("description", sa.String),
    )
    inserts = [
        {"slug": slug, "description": description}
        for slug, description in PERMISSIONS
        if slug not in existing_permissions
    ]
    if inserts:
        op.bulk_insert(permissions_table, inserts)

    role_ids = dict(connection.execute(sa.text("select slug, id from roles")).all())
    permission_ids = dict(connection.execute(sa.text("select slug, id from permissions")).all())
    existing_pairs = set(
        connection.execute(sa.text("select role_id, permission_id from role_permissions")).all()
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )
    pairs = []
    for permission_slug, _description in PERMISSIONS:
        role_id = role_ids["admin"]
        permission_id = permission_ids[permission_slug]
        if (role_id, permission_id) not in existing_pairs:
            pairs.append({"role_id": role_id, "permission_id": permission_id})
    if pairs:
        op.bulk_insert(role_permissions_table, pairs)


def downgrade() -> None:
    connection = op.get_bind()
    permission_slugs = [permission[0] for permission in PERMISSIONS]
    permission_ids = connection.execute(
        sa.text("select id from permissions where slug in :slugs").bindparams(
            sa.bindparam("slugs", expanding=True)
        ),
        {"slugs": permission_slugs},
    ).scalars().all()
    if permission_ids:
        connection.execute(
            sa.text("delete from role_permissions where permission_id in :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": permission_ids},
        )
        connection.execute(
            sa.text("delete from permissions where id in :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": permission_ids},
        )

    op.drop_index("ix_core_backups_status", table_name="core_backups")
    op.drop_table("core_backups")
