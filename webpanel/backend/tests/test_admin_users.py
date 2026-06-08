from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth.security import create_access_token, hash_password, verify_password
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


def _seed_admin() -> str:
    with TestingSessionLocal() as db:
        core_admin = Permission(slug="core.admin", description="Admin")
        admin_role = Role(slug="admin", name="Admin", permissions=[core_admin])
        operator_role = Role(slug="operator", name="Operator")
        viewer_role = Role(slug="viewer", name="Viewer")
        admin = User(
            email="admin@example.com",
            display_name="Admin",
            password_hash=hash_password("AdminPassword123!"),
            roles=[admin_role],
            is_active=True,
            is_superuser=True,
        )
        db.add_all([admin, operator_role, viewer_role])
        db.commit()
        return create_access_token(admin.id)


def _seed_viewer() -> str:
    with TestingSessionLocal() as db:
        role = Role(slug="viewer", name="Viewer")
        user = User(
            email="viewer@example.com",
            display_name="Viewer",
            password_hash="not-used",
            roles=[role],
        )
        db.add(user)
        db.commit()
        return create_access_token(user.id)


def test_admin_can_manage_users_and_audit_events() -> None:
    token = _seed_admin()
    client = TestClient(app)

    create_response = client.post(
        "/api/core/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "operator@example.com",
            "display_name": "Operator",
            "password": "OperatorPassword123!",
            "role_slugs": ["viewer"],
        },
    )
    assert create_response.status_code == 201
    created_user = create_response.json()
    user_id = created_user["id"]
    assert created_user["roles"] == ["viewer"]

    list_response = client.get(
        "/api/core/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert [user["email"] for user in list_response.json()] == [
        "admin@example.com",
        "operator@example.com",
    ]

    active_response = client.patch(
        f"/api/core/admin/users/{user_id}/active",
        headers={"Authorization": f"Bearer {token}"},
        json={"is_active": False},
    )
    assert active_response.status_code == 200
    assert active_response.json()["is_active"] is False

    roles_response = client.patch(
        f"/api/core/admin/users/{user_id}/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"role_slugs": ["operator"]},
    )
    assert roles_response.status_code == 200
    assert roles_response.json()["roles"] == ["operator"]

    password_response = client.patch(
        f"/api/core/admin/users/{user_id}/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"password": "ResetPassword123!"},
    )
    assert password_response.status_code == 200

    with TestingSessionLocal() as db:
        user = db.get(User, user_id)
        actions = set(db.scalars(select(AuditEvent.action)).all())

    assert user is not None
    assert verify_password("ResetPassword123!", user.password_hash)
    assert {
        "users.created",
        "users.active_status.updated",
        "users.roles.updated",
        "users.password_reset",
    }.issubset(actions)


def test_admin_can_view_roles_with_permissions_and_users() -> None:
    token = _seed_admin()
    client = TestClient(app)

    response = client.get("/api/core/admin/roles", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    roles = {role["slug"]: role for role in response.json()}
    assert set(roles) == {"admin", "operator", "viewer"}
    assert roles["admin"]["permissions"] == ["core.admin"]
    assert roles["admin"]["users"] == [
        {
            "id": roles["admin"]["users"][0]["id"],
            "email": "admin@example.com",
            "display_name": "Admin",
            "is_active": True,
        }
    ]
    assert roles["operator"]["users"] == []


def test_user_management_requires_core_admin_permission() -> None:
    token = _seed_viewer()
    client = TestClient(app)

    response = client.get("/api/core/admin/users", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_create_user_rejects_weak_password() -> None:
    token = _seed_admin()
    client = TestClient(app)

    response = client.post(
        "/api/core/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "operator@example.com",
            "display_name": "Operator",
            "password": "weak",
            "role_slugs": ["viewer"],
        },
    )

    assert response.status_code == 400
    assert "Password must be at least 12 characters." in response.json()["detail"]
