"""web module scaffold

Revision ID: 20260611_0010
Revises: 20260605_0009
Create Date: 2026-06-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260611_0010"
down_revision: str | None = "20260605_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSIONS = [
    ("web.view", "View Web module scaffold status."),
]


def upgrade() -> None:
    connection = op.get_bind()
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
    existing_modules = set(connection.execute(sa.text("select slug from modules")).scalars().all())
    if "web" not in existing_modules:
        op.bulk_insert(
            modules_table,
            [
                {
                    "slug": "web",
                    "name": "Web",
                    "version": "0.1.0",
                    "state": "available",
                    "enabled": False,
                    "locked": False,
                    "installed": False,
                }
            ],
        )
    else:
        connection.execute(
            sa.text(
                "update modules set name = :name, state = :state, enabled = :enabled, "
                "locked = :locked, installed = :installed where slug = :slug"
            ),
            {
                "slug": "web",
                "name": "Web",
                "state": "available",
                "enabled": False,
                "locked": False,
                "installed": False,
            },
        )

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
    for role_slug in ("admin", "operator", "viewer"):
        role_id = role_ids.get(role_slug)
        permission_id = permission_ids.get("web.view")
        if role_id is not None and permission_id is not None and (role_id, permission_id) not in existing_pairs:
            pairs.append({"role_id": role_id, "permission_id": permission_id})
    if pairs:
        op.bulk_insert(role_permissions_table, pairs)


def downgrade() -> None:
    connection = op.get_bind()
    permission_ids = connection.execute(
        sa.text("select id from permissions where slug = 'web.view'")
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

    connection.execute(
        sa.text(
            "update modules set state = :state, enabled = :enabled, locked = :locked, "
            "installed = :installed where slug = :slug"
        ),
        {"slug": "web", "state": "locked", "enabled": False, "locked": True, "installed": False},
    )
