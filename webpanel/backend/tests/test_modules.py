from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth.security import create_access_token
from app.db.base import Base
from app.db.models import Module, Permission, Role, User
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


def test_list_modules_from_database() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestingSessionLocal() as db:
        modules_view = Permission(slug="modules.view", description="View modules")
        role = Role(slug="viewer", name="Viewer", permissions=[modules_view])
        user = User(
            email="viewer@example.com",
            display_name="Viewer",
            password_hash="not-used",
            roles=[role],
        )
        db.add(
            Module(
                slug="core",
                name="Core",
                version="0.1.0",
                state="enabled",
                enabled=True,
                locked=False,
                installed=True,
            )
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id)

    client = TestClient(app)
    response = client.get("/api/core/modules", headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

    assert response.status_code == 200
    assert response.json() == [
        {
            "slug": "core",
            "name": "Core",
            "version": "0.1.0",
            "state": "enabled",
            "enabled": True,
            "locked": False,
            "installed": True,
        }
    ]


def test_get_module_by_slug() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestingSessionLocal() as db:
        modules_view = Permission(slug="modules.view", description="View modules")
        role = Role(slug="viewer", name="Viewer", permissions=[modules_view])
        user = User(
            email="viewer@example.com",
            display_name="Viewer",
            password_hash="not-used",
            roles=[role],
        )
        db.add(
            Module(
                slug="web",
                name="Web",
                version="0.1.0",
                state="locked",
                enabled=False,
                locked=True,
                installed=False,
            )
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id)

    client = TestClient(app)
    response = client.get("/api/core/modules/web", headers={"Authorization": f"Bearer {token}"})

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

    assert response.status_code == 200
    assert response.json()["slug"] == "web"
    assert response.json()["state"] == "locked"


def test_update_module_state_requires_manage_permission() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestingSessionLocal() as db:
        modules_manage = Permission(slug="modules.manage", description="Manage modules")
        role = Role(slug="operator", name="Operator", permissions=[modules_manage])
        user = User(
            email="operator@example.com",
            display_name="Operator",
            password_hash="not-used",
            roles=[role],
        )
        db.add(
            Module(
                slug="logs",
                name="Logs",
                version="0.1.0",
                state="locked",
                enabled=False,
                locked=True,
                installed=False,
            )
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id)

    client = TestClient(app)
    response = client.patch(
        "/api/core/modules/logs",
        headers={"Authorization": f"Bearer {token}"},
        json={"state": "available"},
    )

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

    assert response.status_code == 200
    assert response.json()["state"] == "available"
    assert response.json()["enabled"] is False
    assert response.json()["locked"] is False
    assert response.json()["installed"] is False
