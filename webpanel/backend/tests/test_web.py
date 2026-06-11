from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth.security import create_access_token
from app.db.base import Base
from app.db.models import AuditEvent, Module, Permission, Role, User, WebSite
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


def test_web_sites_registry_create_list_get_and_disable() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)

    create_response = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "Example.COM",
            "root_path": "/srv/www/example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": False,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["domain"] == "example.com"
    assert created["root_path"] == "/srv/www/example.com"
    assert created["status"] == "config_pending"
    assert created["php_runtime"] == "php-8.3"
    assert created["ssl_enabled"] is False

    list_response = client.get("/api/core/web/sites", headers={"Authorization": f"Bearer {token}"})
    assert list_response.status_code == 200
    assert [site["domain"] for site in list_response.json()] == ["example.com"]

    get_response = client.get(
        f"/api/core/web/sites/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["domain"] == "example.com"

    disable_response = client.patch(
        f"/api/core/web/sites/{created['id']}/disable",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["status"] == "disabled"

    with TestingSessionLocal() as db:
        site = db.get(WebSite, created["id"])
        audit_actions = [
            row[0]
            for row in db.query(AuditEvent.action)
            .filter(AuditEvent.target_type == "web_site")
            .order_by(AuditEvent.id)
            .all()
        ]

    assert site is not None
    assert site.status == "disabled"
    assert audit_actions == ["web.site.created", "web.site.disabled"]


def test_web_sites_create_requires_manage_permission() -> None:
    token = _token_with_permissions(["web.sites.view"])
    client = TestClient(app)

    response = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "example.com",
            "root_path": "/srv/www/example.com",
            "php_runtime": "none",
            "ssl_enabled": False,
        },
    )

    assert response.status_code == 403


def test_nginx_preview_is_view_only_and_audited() -> None:
    token = _token_with_permissions(["web.sites.view"])
    with TestingSessionLocal() as db:
        site = WebSite(
            domain="preview.example.com",
            root_path="/srv/www/preview.example.com",
            status="config_pending",
            php_runtime="php-8.3",
            ssl_enabled=False,
        )
        db.add(site)
        db.commit()
        site_id = site.id

    client = TestClient(app)
    response = client.get(
        f"/api/core/web/sites/{site_id}/nginx-preview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["site_id"] == site_id
    assert payload["domain"] == "preview.example.com"
    assert payload["saved"] is False
    assert "server_name preview.example.com;" in payload["config"]
    assert "root /srv/www/preview.example.com;" in payload["config"]
    assert "index index.php index.html;" in payload["config"]
    assert "access_log /var/log/nginx/hostpilot/preview.example.com.access.log;" in payload["config"]
    assert "error_log /var/log/nginx/hostpilot/preview.example.com.error.log;" in payload["config"]
    assert "fastcgi_pass unix:/run/php/php8.3-fpm.sock;" in payload["config"]

    with TestingSessionLocal() as db:
        site = db.get(WebSite, site_id)
        audit_event = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "web.site.nginx_preview.generated")
            .one()
        )

    assert site is not None
    assert site.status == "config_pending"
    assert audit_event.target_id == str(site_id)


def test_nginx_preview_requires_sites_view_permission() -> None:
    token = _token_with_permissions(["web.view"])
    with TestingSessionLocal() as db:
        site = WebSite(
            domain="blocked.example.com",
            root_path="/srv/www/blocked.example.com",
            status="config_pending",
            php_runtime="none",
            ssl_enabled=False,
        )
        db.add(site)
        db.commit()
        site_id = site.id

    client = TestClient(app)
    response = client.get(
        f"/api/core/web/sites/{site_id}/nginx-preview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
