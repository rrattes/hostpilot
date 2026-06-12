"""repair web sites admin permissions

Revision ID: 20260612_0014
Revises: 20260611_0013
Create Date: 2026-06-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260612_0014"
down_revision: str | None = "20260611_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSIONS = [
    ("web.sites.view", "View Web site registry records."),
    ("web.sites.manage", "Create and disable Web site registry records."),
]


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
    role_permission_slugs = {
        "admin": ["web.sites.view", "web.sites.manage"],
        "operator": ["web.sites.view", "web.sites.manage"],
        "viewer": ["web.sites.view"],
    }
    pairs = []
    for role_slug, permission_slugs in role_permission_slugs.items():
        role_id = role_ids.get(role_slug)
        if role_id is None:
            continue
        for permission_slug in permission_slugs:
            permission_id = permission_ids.get(permission_slug)
            if permission_id is not None and (role_id, permission_id) not in existing_pairs:
                pairs.append({"role_id": role_id, "permission_id": permission_id})
    if pairs:
        op.bulk_insert(role_permissions_table, pairs)


def downgrade() -> None:
    # Keep permissions assigned. This migration repairs missing RBAC grants in existing installs.
    pass
