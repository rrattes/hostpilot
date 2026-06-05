"""seed core rbac

Revision ID: 20260605_0003
Revises: 20260605_0002
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0003"
down_revision: str | None = "20260605_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSIONS = [
    ("core.view", "View Core status and profile data."),
    ("core.admin", "Access Core administrative endpoints."),
    ("modules.view", "View module registry entries."),
    ("modules.manage", "Manage module registry state."),
    ("audit.view", "View audit events."),
    ("jobs.view", "View jobs."),
    ("settings.view", "View settings."),
    ("settings.edit", "Edit settings."),
]

ROLE_PERMISSIONS = {
    "admin": [permission[0] for permission in PERMISSIONS],
    "viewer": ["core.view", "modules.view", "audit.view", "jobs.view", "settings.view"],
    "operator": [
        "core.view",
        "modules.view",
        "modules.manage",
        "audit.view",
        "jobs.view",
        "settings.view",
        "settings.edit",
    ],
}


def upgrade() -> None:
    connection = op.get_bind()
    permissions_table = sa.table(
        "permissions",
        sa.column("slug", sa.String),
        sa.column("description", sa.String),
    )

    existing_permissions = set(
        connection.execute(sa.text("select slug from permissions")).scalars().all()
    )
    permissions_to_insert = [
        {"slug": slug, "description": description}
        for slug, description in PERMISSIONS
        if slug not in existing_permissions
    ]
    if permissions_to_insert:
        op.bulk_insert(permissions_table, permissions_to_insert)

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
    role_permissions = []
    for role_slug, permission_slugs in ROLE_PERMISSIONS.items():
        role_id = role_ids[role_slug]
        for permission_slug in permission_slugs:
            permission_id = permission_ids[permission_slug]
            if (role_id, permission_id) not in existing_pairs:
                role_permissions.append({"role_id": role_id, "permission_id": permission_id})

    if role_permissions:
        op.bulk_insert(role_permissions_table, role_permissions)


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
