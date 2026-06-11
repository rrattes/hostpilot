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


def setup_function() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _token_with_permissions(permission_slugs: list[str]) -> str:
    with TestingSessionLocal() as db:
        permissions = [
            Permission(slug=permission_slug, description="")
            for permission_slug in permission_slugs
        ]
        role = Role(slug="viewer", name="Viewer", permissions=permissions)
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
                state="available",
                enabled=False,
                locked=False,
                installed=False,
            )
        )
        db.add(user)
        db.commit()
        return create_access_token(user.id)


def test_web_status_is_placeholder_only() -> None:
    token = _token_with_permissions(["web.view"])
    client = TestClient(app)

    response = client.get("/api/core/web/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["module_slug"] == "web"
    assert payload["module_state"] == "available"
    assert payload["enabled"] is False
    assert payload["operational"] is False
    assert [section["slug"] for section in payload["sections"]] == [
        "sites",
        "nginx",
        "ssl",
        "logs",
        "php-runtime",
    ]
    assert all(section["action_available"] is False for section in payload["sections"])


def test_web_status_requires_web_view_permission() -> None:
    token = _token_with_permissions(["core.view"])
    client = TestClient(app)

    response = client.get("/api/core/web/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
