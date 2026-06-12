from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.agent_gateway.contracts import AgentActionResponse
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


def test_web_status_exposes_available_site_workflows() -> None:
    token = _token_with_permissions(["web.view"])
    client = TestClient(app)

    response = client.get("/api/core/web/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["module_slug"] == "web"
    assert payload["module_state"] == "available"
    assert payload["enabled"] is False
    assert payload["operational"] is True
    assert [section["slug"] for section in payload["sections"]] == [
        "sites",
        "nginx",
        "ssl",
        "logs",
        "php-runtime",
    ]
    actions_by_slug = {section["slug"]: section["action_available"] for section in payload["sections"]}
    assert actions_by_slug == {
        "sites": True,
        "nginx": True,
        "ssl": False,
        "logs": True,
        "php-runtime": False,
    }


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


def test_nginx_apply_plan_requires_ready_to_apply_status() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "plan-draft.example.com",
            "root_path": "/var/www/hostpilot-sites/plan-draft.example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": False,
        },
    ).json()

    response = client.get(
        f"/api/core/web/sites/{created['id']}/nginx-apply-plan",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_nginx_apply_plan_is_preview_only_and_audited() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "plan.example.com",
            "root_path": "/var/www/hostpilot-sites/plan.example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": False,
        },
    ).json()
    client.get(
        f"/api/core/web/sites/{created['id']}/nginx-preview",
        headers={"Authorization": f"Bearer {token}"},
    )
    client.patch(
        f"/api/core/web/sites/{created['id']}/mark-ready",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        f"/api/core/web/sites/{created['id']}/nginx-apply-plan",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["site_id"] == created["id"]
    assert payload["domain"] == "plan.example.com"
    assert payload["target_config_path"] == "/etc/nginx/sites-available/hostpilot/plan.example.com.conf"
    assert payload["webroot_path"] == "/var/www/hostpilot-sites/plan.example.com"
    assert payload["config_filename"] == "plan.example.com.conf"
    assert payload["required_directories"] == [
        "/var/www/hostpilot-sites/plan.example.com",
        "/etc/nginx/sites-available",
        "/etc/nginx/sites-available/hostpilot",
        "/etc/nginx/sites-enabled",
        "/var/log/nginx/hostpilot",
    ]
    assert payload["validation_commands"] == [
        "nginx -t",
        "test -f /etc/nginx/sites-available/hostpilot/plan.example.com.conf",
        "test -d /var/www/hostpilot-sites/plan.example.com",
    ]
    assert payload["service_reload_command"] == "systemctl reload nginx"
    assert payload["risk_level"] == "medium"
    assert payload["confirmation_phrase"] == "APPLY NGINX PLAN plan.example.com"
    assert payload["plan_only"] is True

    with TestingSessionLocal() as db:
        audit_event = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "web.site.nginx_apply_plan.generated")
            .one()
        )

    assert audit_event.target_id == str(created["id"])


def test_nginx_dry_run_requires_ready_to_apply_status() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "dry-draft.example.com",
            "root_path": "/var/www/hostpilot-sites/dry-draft.example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": False,
        },
    ).json()

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-dry-run",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "APPLY NGINX PLAN dry-draft.example.com"},
    )

    assert response.status_code == 409


def test_nginx_dry_run_requires_confirmation_phrase() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "dry-confirm.example.com",
            "root_path": "/var/www/hostpilot-sites/dry-confirm.example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": False,
        },
    ).json()
    client.get(
        f"/api/core/web/sites/{created['id']}/nginx-preview",
        headers={"Authorization": f"Bearer {token}"},
    )
    client.patch(
        f"/api/core/web/sites/{created['id']}/mark-ready",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-dry-run",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "wrong phrase"},
    )

    assert response.status_code == 400


def test_nginx_dry_run_simulates_apply_without_changes_and_audits() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": "dry.example.com",
            "root_path": "/var/www/hostpilot-sites/dry.example.com",
            "php_runtime": "php-8.3",
            "ssl_enabled": False,
        },
    ).json()
    client.get(
        f"/api/core/web/sites/{created['id']}/nginx-preview",
        headers={"Authorization": f"Bearer {token}"},
    )
    client.patch(
        f"/api/core/web/sites/{created['id']}/mark-ready",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-dry-run",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "APPLY NGINX PLAN dry.example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["site_id"] == created["id"]
    assert payload["domain"] == "dry.example.com"
    assert "server_name dry.example.com;" in payload["config_content"]
    assert payload["target_config_path"] == "/etc/nginx/sites-available/hostpilot/dry.example.com.conf"
    assert payload["webroot_path"] == "/var/www/hostpilot-sites/dry.example.com"
    assert payload["directory_checks"] == [
        "would ensure directory exists: /var/www/hostpilot-sites/dry.example.com",
        "would ensure directory exists: /etc/nginx/sites-available",
        "would ensure directory exists: /etc/nginx/sites-available/hostpilot",
        "would ensure directory exists: /etc/nginx/sites-enabled",
        "would ensure directory exists: /var/log/nginx/hostpilot",
    ]
    assert payload["nginx_validation_command"] == "nginx -t"
    assert payload["reload_command"] == "systemctl reload nginx"
    assert payload["executed"] is False
    assert payload["wrote_files"] is False

    with TestingSessionLocal() as db:
        audit_actions = [
            row[0]
            for row in db.query(AuditEvent.action)
            .filter(
                AuditEvent.target_type == "web_site",
                AuditEvent.target_id == str(created["id"]),
                AuditEvent.action.like("web.site.nginx_dry_run%"),
            )
            .order_by(AuditEvent.id)
            .all()
        ]

    assert audit_actions == [
        "web.site.nginx_dry_run.requested",
        "web.site.nginx_dry_run.completed",
    ]


def test_controlled_nginx_apply_calls_agent_and_updates_site(monkeypatch) -> None:
    captured_payload: dict[str, object] | None = None

    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        nonlocal captured_payload
        captured_payload = payload
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="completed",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=True,
            status="applied",
            data={"applied": True, "reloaded": True},
            error=None,
            duration_ms=3,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _ready_site(client, token, "apply-agent.example.com")

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-apply",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "APPLY NGINX PLAN apply-agent.example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["site"]["status"] == "applied"
    assert payload["site"]["provisioning_status"] == "ready_to_apply"
    assert payload["result"]["reloaded"] is True
    assert captured_payload is not None
    assert captured_payload["target_config_path"] == (
        "/etc/nginx/sites-available/hostpilot/apply-agent.example.com.conf"
    )
    assert captured_payload["allowed_nginx_base"] == "/etc/nginx/sites-available/hostpilot"


def test_controlled_nginx_apply_marks_error_on_agent_failure(monkeypatch) -> None:
    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="failed",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=False,
            status="validation_failed",
            data={"rolled_back": True, "reloaded": False},
            error="validation_failed",
            duration_ms=4,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _ready_site(client, token, "apply-fail.example.com")

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-apply",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "APPLY NGINX PLAN apply-fail.example.com"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["site"]["status"] == "error"
    assert response.json()["site"]["provisioning_status"] == "error"
    assert response.json()["result"]["rolled_back"] is True


def test_controlled_nginx_apply_requires_confirmation_phrase() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _ready_site(client, token, "apply-confirm.example.com")

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-apply",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "wrong phrase"},
    )

    assert response.status_code == 400


def test_controlled_nginx_apply_requires_manage_permission() -> None:
    manager_token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _ready_site(client, manager_token, "apply-rbac.example.com")
    with TestingSessionLocal() as db:
        permission = db.query(Permission).filter(Permission.slug == "web.sites.view").one()
        role = Role(slug="viewer-rbac", name="Viewer RBAC", permissions=[permission])
        user = User(
            email="viewer-rbac@example.com",
            display_name="Viewer RBAC",
            password_hash="not-used",
            roles=[role],
        )
        db.add(user)
        db.commit()
        viewer_token = create_access_token(user.id)

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-apply",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"confirmation_phrase": "APPLY NGINX PLAN apply-rbac.example.com"},
    )

    assert response.status_code == 403


def test_controlled_nginx_disable_calls_agent_and_updates_site(monkeypatch) -> None:
    captured_payload: dict[str, object] | None = None

    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        nonlocal captured_payload
        captured_payload = payload
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="completed",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=True,
            status="disabled",
            data={"disabled": True, "reloaded": True},
            error=None,
            duration_ms=3,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _applied_site(client, token, "disable-agent.example.com")

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-disable",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "DISABLE NGINX SITE disable-agent.example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["site"]["status"] == "disabled"
    assert payload["site"]["provisioning_status"] == "disabled"
    assert payload["result"]["reloaded"] is True
    assert captured_payload is not None
    assert captured_payload["target_config_path"] == (
        "/etc/nginx/sites-available/hostpilot/disable-agent.example.com.conf"
    )
    assert captured_payload["allowed_nginx_base"] == "/etc/nginx/sites-available/hostpilot"

    with TestingSessionLocal() as db:
        audit_actions = [
            row[0]
            for row in db.query(AuditEvent.action)
            .filter(
                AuditEvent.target_type == "web_site",
                AuditEvent.target_id == str(created["id"]),
                AuditEvent.action.like("web.site.nginx_disable%"),
            )
            .order_by(AuditEvent.id)
            .all()
        ]
    assert audit_actions == [
        "web.site.nginx_disable.requested",
        "web.site.nginx_disable.completed",
    ]


def test_controlled_nginx_disable_marks_error_on_validation_failure(monkeypatch) -> None:
    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="failed",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=False,
            status="validation_failed",
            data={"rolled_back": True, "reloaded": False},
            error="validation_failed",
            duration_ms=4,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _applied_site(client, token, "disable-fail.example.com")

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-disable",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "DISABLE NGINX SITE disable-fail.example.com"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["site"]["status"] == "error"
    assert response.json()["site"]["provisioning_status"] == "error"
    assert response.json()["result"]["rolled_back"] is True


def test_controlled_nginx_disable_requires_applied_site_and_confirmation() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _ready_site(client, token, "disable-confirm.example.com")

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-disable",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "DISABLE NGINX SITE disable-confirm.example.com"},
    )
    assert response.status_code == 409

    _mark_site_applied(created["id"])
    wrong_phrase = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-disable",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "wrong phrase"},
    )
    assert wrong_phrase.status_code == 400


def test_controlled_nginx_disable_requires_manage_permission() -> None:
    manager_token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _applied_site(client, manager_token, "disable-rbac.example.com")
    with TestingSessionLocal() as db:
        permission = db.query(Permission).filter(Permission.slug == "web.sites.view").one()
        role = Role(slug="disable-viewer-rbac", name="Disable Viewer RBAC", permissions=[permission])
        user = User(
            email="disable-viewer-rbac@example.com",
            display_name="Disable Viewer RBAC",
            password_hash="not-used",
            roles=[role],
        )
        db.add(user)
        db.commit()
        viewer_token = create_access_token(user.id)

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-disable",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"confirmation_phrase": "DISABLE NGINX SITE disable-rbac.example.com"},
    )

    assert response.status_code == 403


def test_controlled_nginx_reapply_calls_apply_agent_and_updates_site(monkeypatch) -> None:
    captured_action: str | None = None
    captured_payload: dict[str, object] | None = None

    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        nonlocal captured_action, captured_payload
        captured_action = action
        captured_payload = payload
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="completed",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=True,
            status="applied",
            data={"applied": True, "reloaded": True},
            error=None,
            duration_ms=3,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _disabled_site(client, token, "reapply-agent.example.com")

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-reapply",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "APPLY NGINX PLAN reapply-agent.example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["site"]["status"] == "applied"
    assert payload["site"]["provisioning_status"] == "ready_to_apply"
    assert captured_action == "web.nginx.apply_site_config"
    assert captured_payload is not None
    assert captured_payload["target_config_path"] == (
        "/etc/nginx/sites-available/hostpilot/reapply-agent.example.com.conf"
    )

    with TestingSessionLocal() as db:
        audit_actions = [
            row[0]
            for row in db.query(AuditEvent.action)
            .filter(
                AuditEvent.target_type == "web_site",
                AuditEvent.target_id == str(created["id"]),
                AuditEvent.action.like("web.site.nginx_reapply%"),
            )
            .order_by(AuditEvent.id)
            .all()
        ]
    assert audit_actions == [
        "web.site.nginx_reapply.requested",
        "web.site.nginx_reapply.completed",
    ]


def test_controlled_nginx_reapply_rejects_unsafe_path_before_agent(monkeypatch) -> None:
    called = False

    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        nonlocal called
        called = True
        raise AssertionError("Agent should not be called for unsafe readiness")

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _disabled_site(client, token, "reapply-unsafe.example.com")
    _mutate_site(created["id"], root_path="/etc")

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-reapply",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "APPLY NGINX PLAN reapply-unsafe.example.com"},
    )

    assert response.status_code == 409
    assert "Safe root path" in response.json()["detail"]
    assert called is False


def test_controlled_nginx_reapply_requires_readiness(monkeypatch) -> None:
    called = False

    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        nonlocal called
        called = True
        raise AssertionError("Agent should not be called when readiness fails")

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _disabled_site(client, token, "reapply-readiness.example.com")
    _mutate_site(created["id"], ssl_enabled=True)

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-reapply",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "APPLY NGINX PLAN reapply-readiness.example.com"},
    )

    assert response.status_code == 409
    assert "SSL disabled/pending" in response.json()["detail"]
    assert called is False


def test_controlled_nginx_reapply_marks_error_on_apply_failure(monkeypatch) -> None:
    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="failed",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=False,
            status="validation_failed",
            data={"rolled_back": True, "reloaded": False},
            error="validation_failed",
            duration_ms=4,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _error_site(client, token, "reapply-fail.example.com")

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-reapply",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "APPLY NGINX PLAN reapply-fail.example.com"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["site"]["status"] == "error"
    assert response.json()["site"]["provisioning_status"] == "error"
    assert response.json()["result"]["rolled_back"] is True


def test_controlled_nginx_reapply_requires_disabled_or_error_status() -> None:
    token = _token_with_permissions(["web.sites.view", "web.sites.manage"])
    client = TestClient(app)
    created = _applied_site(client, token, "reapply-status.example.com")

    response = client.post(
        f"/api/core/web/sites/{created['id']}/nginx-reapply",
        headers={"Authorization": f"Bearer {token}"},
        json={"confirmation_phrase": "APPLY NGINX PLAN reapply-status.example.com"},
    )

    assert response.status_code == 409


def test_web_site_logs_calls_agent_with_allowed_log_base_and_returns_lines(monkeypatch) -> None:
    captured_payload: dict[str, object] | None = None

    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        nonlocal captured_payload
        captured_payload = payload
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="completed",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=True,
            status="completed",
            data={
                "line_limit": 2,
                "logs": {
                    "access": {
                        "path": "/var/log/nginx/hostpilot/logs-agent.example.com.access.log",
                        "missing": False,
                        "lines": ["access-1", "access-2"],
                    },
                    "error": {
                        "path": "/var/log/nginx/hostpilot/logs-agent.example.com.error.log",
                        "missing": False,
                        "lines": ["error-1"],
                    },
                },
            },
            error=None,
            duration_ms=2,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view"])
    client = TestClient(app)
    created = _site_record("logs-agent.example.com")

    response = client.get(
        f"/api/core/web/sites/{created['id']}/logs?lines=2",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access"]["lines"] == ["access-1", "access-2"]
    assert payload["error"]["lines"] == ["error-1"]
    assert captured_payload == {
        "domain": "logs-agent.example.com",
        "line_limit": 2,
        "allowed_log_base": "/var/log/nginx/hostpilot",
    }

    with TestingSessionLocal() as db:
        audit_action = (
            db.query(AuditEvent.action)
            .filter(
                AuditEvent.target_type == "web_site",
                AuditEvent.target_id == str(created["id"]),
                AuditEvent.action == "web.site.logs.accessed",
            )
            .one()[0]
        )
    assert audit_action == "web.site.logs.accessed"


def test_web_site_logs_preserves_missing_log_file_state(monkeypatch) -> None:
    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="completed",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=True,
            status="completed",
            data={
                "line_limit": 100,
                "logs": {
                    "access": {"path": "/var/log/nginx/hostpilot/missing.example.com.access.log", "missing": True, "lines": []},
                    "error": {"path": "/var/log/nginx/hostpilot/missing.example.com.error.log", "missing": True, "lines": []},
                },
            },
            error=None,
            duration_ms=2,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view"])
    client = TestClient(app)
    created = _site_record("missing.example.com")

    response = client.get(
        f"/api/core/web/sites/{created['id']}/logs",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["access"]["missing"] is True
    assert response.json()["access"]["lines"] == []
    assert response.json()["error"]["missing"] is True


def test_web_site_logs_rejects_line_limit_above_max() -> None:
    token = _token_with_permissions(["web.sites.view"])
    client = TestClient(app)
    created = _site_record("logs-limit.example.com")

    response = client.get(
        f"/api/core/web/sites/{created['id']}/logs?lines=501",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_web_site_logs_returns_error_when_agent_rejects_unsafe_path(monkeypatch) -> None:
    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="rejected",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=False,
            status="rejected",
            data={},
            error="Access log path must match the site domain under the allowed log path.",
            duration_ms=2,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view"])
    client = TestClient(app)
    created = _site_record("logs-reject.example.com")

    response = client.get(
        f"/api/core/web/sites/{created['id']}/logs",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 502
    assert "Access log path" in response.json()["detail"]


def test_web_site_files_calls_agent_with_site_root_and_returns_entries(monkeypatch) -> None:
    captured_payload: dict[str, object] | None = None

    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        nonlocal captured_payload
        captured_payload = payload
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="completed",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=True,
            status="completed",
            data={
                "root_path": "/var/www/hostpilot-sites/files-agent.example.com",
                "relative_subpath": "public",
                "target_path": "/var/www/hostpilot-sites/files-agent.example.com/public",
                "page": 1,
                "page_size": 50,
                "max_depth": 1,
                "total_entries": 2,
                "has_next": False,
                "entries": [
                    {
                        "name": "assets",
                        "type": "directory",
                        "size": 4096,
                        "modified_at": 10.0,
                        "relative_path": "public/assets",
                    },
                    {
                        "name": "index.html",
                        "type": "file",
                        "size": 120,
                        "modified_at": 20.0,
                        "relative_path": "public/index.html",
                    },
                ],
            },
            error=None,
            duration_ms=2,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view"])
    client = TestClient(app)
    created = _site_record("files-agent.example.com")

    response = client.get(
        f"/api/core/web/sites/{created['id']}/files?subpath=public",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["entries"][0]["name"] == "assets"
    assert payload["entries"][1]["type"] == "file"
    assert captured_payload == {
        "root_path": "/var/www/hostpilot-sites/files-agent.example.com",
        "relative_subpath": "public",
        "page": 1,
        "page_size": 50,
        "allowed_webroot_base": "/var/www/hostpilot-sites",
    }


def test_web_site_files_rejects_traversal_before_agent(monkeypatch) -> None:
    called = False

    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        nonlocal called
        called = True
        raise AssertionError("Agent should not be called for traversal")

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view"])
    client = TestClient(app)
    created = _site_record("files-traversal.example.com")

    response = client.get(
        f"/api/core/web/sites/{created['id']}/files?subpath=../other",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert called is False


def test_web_site_files_enforces_root_boundary_before_agent(monkeypatch) -> None:
    called = False

    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        nonlocal called
        called = True
        raise AssertionError("Agent should not be called for unsafe root")

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view"])
    client = TestClient(app)
    created = _site_record("files-root.example.com")
    _mutate_site(created["id"], root_path="/etc")

    response = client.get(
        f"/api/core/web/sites/{created['id']}/files",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert called is False


def test_web_site_files_preserves_missing_directory_state(monkeypatch) -> None:
    def fake_execute_agent_action(db: Session, *, action: str, payload: dict[str, object], user: User):
        from app.db.models import Job

        job = Job(
            type="agent_action",
            module="agent",
            action=action,
            status="missing_directory",
            payload="{}",
            result="{}",
        )
        db.add(job)
        db.flush()
        return job, AgentActionResponse(
            success=True,
            status="missing_directory",
            data={
                "root_path": "/var/www/hostpilot-sites/files-missing.example.com",
                "relative_subpath": "missing",
                "target_path": "/var/www/hostpilot-sites/files-missing.example.com/missing",
                "page": 1,
                "page_size": 50,
                "max_depth": 1,
                "total_entries": 0,
                "has_next": False,
                "entries": [],
            },
            error=None,
            duration_ms=2,
        )

    monkeypatch.setattr("app.api.web.execute_mock_agent_action", fake_execute_agent_action)
    token = _token_with_permissions(["web.sites.view"])
    client = TestClient(app)
    created = _site_record("files-missing.example.com")

    response = client.get(
        f"/api/core/web/sites/{created['id']}/files?subpath=missing",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "missing_directory"
    assert response.json()["entries"] == []


def test_web_site_files_rejects_page_size_above_max() -> None:
    token = _token_with_permissions(["web.sites.view"])
    client = TestClient(app)
    created = _site_record("files-limit.example.com")

    response = client.get(
        f"/api/core/web/sites/{created['id']}/files?page_size=101",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def _ready_site(client: TestClient, token: str, domain: str) -> dict[str, object]:
    created = client.post(
        "/api/core/web/sites",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "domain": domain,
            "root_path": f"/var/www/hostpilot-sites/{domain}",
            "php_runtime": "php-8.3",
            "ssl_enabled": False,
        },
    ).json()
    client.get(
        f"/api/core/web/sites/{created['id']}/nginx-preview",
        headers={"Authorization": f"Bearer {token}"},
    )
    client.patch(
        f"/api/core/web/sites/{created['id']}/mark-ready",
        headers={"Authorization": f"Bearer {token}"},
    )
    return created


def _site_record(domain: str) -> dict[str, object]:
    with TestingSessionLocal() as db:
        site = WebSite(
            domain=domain,
            root_path=f"/var/www/hostpilot-sites/{domain}",
            status="config_pending",
            provisioning_status="draft",
            php_runtime="php-8.3",
            ssl_enabled=False,
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        return {"id": site.id, "domain": site.domain}


def _applied_site(client: TestClient, token: str, domain: str) -> dict[str, object]:
    created = _ready_site(client, token, domain)
    _mark_site_applied(created["id"])
    return created


def _disabled_site(client: TestClient, token: str, domain: str) -> dict[str, object]:
    created = _ready_site(client, token, domain)
    _mutate_site(created["id"], status="disabled", provisioning_status="disabled")
    return created


def _error_site(client: TestClient, token: str, domain: str) -> dict[str, object]:
    created = _ready_site(client, token, domain)
    _mutate_site(created["id"], status="error", provisioning_status="error")
    return created


def _mark_site_applied(site_id: object) -> None:
    _mutate_site(site_id, status="applied", provisioning_status="ready_to_apply")


def _mutate_site(site_id: object, **changes: object) -> None:
    with TestingSessionLocal() as db:
        site = db.get(WebSite, site_id)
        assert site is not None
        for key, value in changes.items():
            setattr(site, key, value)
        db.commit()
