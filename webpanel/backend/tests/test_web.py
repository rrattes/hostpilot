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
            "root_path": "/var/www/hostpilot-sites/example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": False,
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["domain"] == "example.com"
    assert created["root_path"] == "/var/www/hostpilot-sites/example.com"
    assert created["status"] == "config_pending"
    assert created["provisioning_status"] == "draft"
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
            "root_path": "/var/www/hostpilot-sites/example.com",
            "php_runtime": "none",
            "ssl_enabled": False,
        },
    )

    assert response.status_code == 403


def test_web_sites_reject_invalid_domains() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)

    for domain in ["", "localhost", "-example.com", "example..com", "https://example.com"]:
        response = client.post(
            "/api/core/web/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "domain": domain,
                "root_path": "/var/www/hostpilot-sites/example.com",
                "php_runtime": "none",
                "ssl_enabled": False,
            },
        )
        assert response.status_code == 422


def test_web_sites_reject_invalid_root_paths() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)

    for root_path in [
        "/",
        "/etc",
        "/bin",
        "/usr",
        "/var",
        "/home",
        "relative/path",
        "/var/www/hostpilot-sites/../escape",
        "/var/www/other/example.com",
    ]:
        response = client.post(
            "/api/core/web/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "domain": "example.com",
                "root_path": root_path,
                "php_runtime": "none",
                "ssl_enabled": False,
            },
        )
        assert response.status_code == 422


def test_web_sites_prevent_duplicate_domains_on_create_and_update() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)

    first = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "first.example.com",
            "root_path": "/var/www/hostpilot-sites/first.example.com",
            "php_runtime": "none",
            "ssl_enabled": False,
        },
    )
    second = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "second.example.com",
            "root_path": "/var/www/hostpilot-sites/second.example.com",
            "php_runtime": "none",
            "ssl_enabled": False,
        },
    )
    duplicate_create = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "FIRST.example.com",
            "root_path": "/var/www/hostpilot-sites/duplicate.example.com",
            "php_runtime": "none",
            "ssl_enabled": False,
        },
    )
    duplicate_update = client.patch(
        f"/api/core/web/sites/{second.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "first.example.com",
            "root_path": "/var/www/hostpilot-sites/second.example.com",
            "php_runtime": "none",
            "ssl_enabled": False,
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert duplicate_create.status_code == 409
    assert duplicate_update.status_code == 409


def test_web_sites_update_validates_and_updates_record_only() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)

    created = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "old.example.com",
            "root_path": "/var/www/hostpilot-sites/old.example.com",
            "php_runtime": "none",
            "ssl_enabled": False,
        },
    ).json()
    updated = client.patch(
        f"/api/core/web/sites/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "new.example.com",
            "root_path": "/var/www/hostpilot-sites/new.example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": True,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["domain"] == "new.example.com"
    assert updated.json()["root_path"] == "/var/www/hostpilot-sites/new.example.com"
    assert updated.json()["php_runtime"] == "php-8.3"
    assert updated.json()["ssl_enabled"] is True


def test_nginx_preview_is_view_only_and_audited() -> None:
    token = _token_with_permissions(["web.sites.view"])
    with TestingSessionLocal() as db:
        site = WebSite(
            domain="preview.example.com",
            root_path="/var/www/hostpilot-sites/preview.example.com",
            status="config_pending",
            provisioning_status="draft",
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
    assert "root /var/www/hostpilot-sites/preview.example.com;" in payload["config"]
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
    assert site.provisioning_status == "config_previewed"
    assert audit_event.target_id == str(site_id)


def test_nginx_preview_requires_sites_view_permission() -> None:
    token = _token_with_permissions(["web.view"])
    with TestingSessionLocal() as db:
        site = WebSite(
            domain="blocked.example.com",
            root_path="/var/www/hostpilot-sites/blocked.example.com",
            status="config_pending",
            provisioning_status="draft",
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


def test_web_site_readiness_requires_preview_before_ready() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "ready.example.com",
            "root_path": "/var/www/hostpilot-sites/ready.example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": False,
        },
    ).json()

    readiness = client.get(
        f"/api/core/web/sites/{created['id']}/readiness",
        headers={"Authorization": f"Bearer {token}"},
    )
    mark_ready = client.patch(
        f"/api/core/web/sites/{created['id']}/mark-ready",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert readiness.status_code == 200
    assert readiness.json()["ready"] is False
    checks = {check["slug"]: check["passed"] for check in readiness.json()["checks"]}
    assert checks == {
        "valid_domain": True,
        "safe_root_path": True,
        "no_duplicate_domain": True,
        "nginx_preview_available": False,
        "ssl_disabled_pending": True,
        "php_runtime_selected": True,
    }
    assert mark_ready.status_code == 409


def test_web_site_can_be_marked_ready_after_preview() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "apply.example.com",
            "root_path": "/var/www/hostpilot-sites/apply.example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": False,
        },
    ).json()

    preview = client.get(
        f"/api/core/web/sites/{created['id']}/nginx-preview",
        headers={"Authorization": f"Bearer {token}"},
    )
    readiness = client.get(
        f"/api/core/web/sites/{created['id']}/readiness",
        headers={"Authorization": f"Bearer {token}"},
    )
    ready = client.patch(
        f"/api/core/web/sites/{created['id']}/mark-ready",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert preview.status_code == 200
    assert readiness.status_code == 200
    assert readiness.json()["ready"] is True
    assert ready.status_code == 200
    assert ready.json()["provisioning_status"] == "ready_to_apply"

    with TestingSessionLocal() as db:
        site = db.get(WebSite, created["id"])
        audit_event = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "web.site.ready_to_apply.marked")
            .one()
        )

    assert site is not None
    assert site.provisioning_status == "ready_to_apply"
    assert audit_event.target_id == str(created["id"])


def test_web_site_readiness_blocks_ssl_until_automation_exists() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "ssl.example.com",
            "root_path": "/var/www/hostpilot-sites/ssl.example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": True,
        },
    ).json()
    client.get(
        f"/api/core/web/sites/{created['id']}/nginx-preview",
        headers={"Authorization": f"Bearer {token}"},
    )

    readiness = client.get(
        f"/api/core/web/sites/{created['id']}/readiness",
        headers={"Authorization": f"Bearer {token}"},
    )

    checks = {check["slug"]: check["passed"] for check in readiness.json()["checks"]}
    assert readiness.json()["ready"] is False
    assert checks["ssl_disabled_pending"] is False
