"""seed agent permissions

Revision ID: 20260605_0007
Revises: 20260605_0006
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0007"
down_revision: str | None = "20260605_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSIONS = [
    ("agent.view", "View mock agent status and recent agent jobs."),
    ("agent.execute_mock", "Execute allowlisted mock agent actions."),
]

ROLE_PERMISSIONS = {
    "admin": ["agent.view", "agent.execute_mock"],
    "operator": ["agent.view", "agent.execute_mock"],
    "viewer": ["agent.view"],
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
    for role_slug, permission_slugs in ROLE_PERMISSIONS.items():
        role_id = role_ids[role_slug]
        for permission_slug in permission_slugs:
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
