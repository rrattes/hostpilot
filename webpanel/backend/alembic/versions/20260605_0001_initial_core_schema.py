"""initial core schema

Revision ID: 20260605_0001
Revises:
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260605_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


timestamp = sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
    )
    op.create_index("ix_roles_slug", "roles", ["slug"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
    )
    op.create_index("ix_permissions_slug", "permissions", ["slug"], unique=True)

    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False, server_default="0.1.0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("installed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
    )
    op.create_index("ix_modules_slug", "modules", ["slug"], unique=True)

    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
    )
    op.create_index("ix_settings_key", "settings", ["key"], unique=True)

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("payload", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="unread"),
        sa.Column("severity", sa.String(length=40), nullable=False, server_default="info"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
    )
    op.create_index("ix_notifications_status", "notifications", ["status"])

    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("os_name", sa.String(length=120), nullable=False),
        sa.Column("is_local", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
    )
    op.create_index("ix_servers_slug", "servers", ["slug"], unique=True)

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), primary_key=True),
        sa.UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions_role_permission",
        ),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("target_type", sa.String(length=120), nullable=False),
        sa.Column("target_id", sa.String(length=120), nullable=True),
        sa.Column("outcome", sa.String(length=40), nullable=False, server_default="success"),
        sa.Column("metadata", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=timestamp),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])

    _seed_core_data()


def downgrade() -> None:
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_index("ix_servers_slug", table_name="servers")
    op.drop_table("servers")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_settings_key", table_name="settings")
    op.drop_table("settings")
    op.drop_index("ix_modules_slug", table_name="modules")
    op.drop_table("modules")
    op.drop_index("ix_permissions_slug", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_slug", table_name="roles")
    op.drop_table("roles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")


def _seed_core_data() -> None:
    roles_table = sa.table(
        "roles",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
    )
    modules_table = sa.table(
        "modules",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("version", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("locked", sa.Boolean),
        sa.column("installed", sa.Boolean),
    )
    servers_table = sa.table(
        "servers",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("hostname", sa.String),
        sa.column("os_name", sa.String),
        sa.column("is_local", sa.Boolean),
    )

    op.bulk_insert(
        roles_table,
        [
            {"slug": "admin", "name": "Admin"},
            {"slug": "operator", "name": "Operator"},
            {"slug": "viewer", "name": "Viewer"},
        ],
    )
    op.bulk_insert(
        modules_table,
        [
            {
                "slug": "core",
                "name": "Core",
                "version": "0.1.0",
                "enabled": True,
                "locked": False,
                "installed": True,
            },
            {
                "slug": "web",
                "name": "Web",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "sites",
                "name": "Sites",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "nginx",
                "name": "Nginx",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "ssl",
                "name": "SSL",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "logs",
                "name": "Logs",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "services",
                "name": "Services",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "updates",
                "name": "Updates",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "backups",
                "name": "Backups",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "php-runtime",
                "name": "PHP Runtime",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "server-system",
                "name": "Server & System",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "remote-access",
                "name": "Remote Access",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "docker-containers",
                "name": "Docker / Containers",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
            {
                "slug": "kvm-virtualization",
                "name": "KVM / Virtualization",
                "version": "0.1.0",
                "enabled": False,
                "locked": True,
                "installed": False,
            },
        ],
    )
    op.bulk_insert(
        servers_table,
        [
            {
                "slug": "local",
                "name": "Local Server",
                "hostname": "hostpilot-local",
                "os_name": "Ubuntu Server 26.04 LTS",
                "is_local": True,
            }
        ],
    )
