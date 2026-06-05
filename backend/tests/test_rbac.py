from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth.security import create_access_token
from app.db.base import Base
from app.db.models import AuditEvent, Permission, Role, User
from app.db.session import get_db
from app.main import app


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_function() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _create_user_with_permissions(
    *,
    email: str,
    role_slug: str,
    permission_slugs: list[str],
) -> str:
    with TestingSessionLocal() as db:
        permissions = [
            Permission(slug=permission_slug, description="")
            for permission_slug in permission_slugs
        ]
        role = Role(slug=role_slug, name=role_slug.title(), permissions=permissions)
        user = User(
            email=email,
            display_name=role_slug.title(),
            password_hash="not-used",
            roles=[role],
        )
        db.add(user)
        db.commit()
        return create_access_token(user.id)


def test_admin_allowed() -> None:
    token = _create_user_with_permissions(
        email="admin@example.com",
        role_slug="admin",
        permission_slugs=["core.admin"],
    )
    client = TestClient(app)

    response = client.get("/api/core/admin/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_viewer_blocked_from_admin_endpoint_and_audited() -> None:
    token = _create_user_with_permissions(
        email="viewer@example.com",
        role_slug="viewer",
        permission_slugs=["core.view"],
    )
    client = TestClient(app)

    response = client.get("/api/core/admin/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    with TestingSessionLocal() as db:
        audit_event = db.scalar(select(AuditEvent).where(AuditEvent.action == "rbac.access_denied"))

    assert audit_event is not None
    assert audit_event.target_id == "core.admin"


def test_unauthenticated_blocked_from_core_status() -> None:
    client = TestClient(app)

    response = client.get("/api/core/status")

    assert response.status_code == 401


def test_current_permissions_endpoint() -> None:
    token = _create_user_with_permissions(
        email="operator@example.com",
        role_slug="operator",
        permission_slugs=["core.view", "modules.view", "settings.edit"],
    )
    client = TestClient(app)

    response = client.get(
        "/api/core/auth/permissions",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "roles": ["operator"],
        "permissions": ["core.view", "modules.view", "settings.edit"],
    }
