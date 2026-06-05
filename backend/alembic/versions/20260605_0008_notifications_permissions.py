"""notifications permissions

Revision ID: 20260605_0008
Revises: 20260605_0007
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0008"
down_revision: str | None = "20260605_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSIONS = [
    ("notifications.view", "View own notifications."),
    ("notifications.manage_own", "Mark own notifications as read."),
]


def upgrade() -> None:
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_notifications_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

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
    for role_slug in ("admin", "operator", "viewer"):
        role_id = role_ids[role_slug]
        for permission_slug, _description in PERMISSIONS:
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

    op.drop_index("ix_notifications_user_id", table_name="notifications")
    with op.batch_alter_table("notifications") as batch_op:
        batch_op.drop_constraint("fk_notifications_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")
