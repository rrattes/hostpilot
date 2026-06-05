from collections.abc import Generator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth.security import create_access_token
from app.db.base import Base
from app.db.models import AuditEvent, Job, Module, Permission, Role, Server, Setting, User
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


def _token(email: str, permission_slugs: list[str]) -> str:
    with TestingSessionLocal() as db:
        permissions = [Permission(slug=slug, description="") for slug in permission_slugs]
        role = Role(slug=email.split("@")[0], name="Test Role", permissions=permissions)
        user = User(email=email, display_name="Test User", password_hash="not-used", roles=[role])
        db.add(user)
        db.commit()
        return create_access_token(user.id)


def test_settings_permissions() -> None:
    view_token = _token("viewer@example.com", ["settings.view"])
    blocked_token = _token("blocked@example.com", ["core.view"])
    with TestingSessionLocal() as db:
        db.add(Setting(key="core.product_name", value="HostPilot"))
        db.commit()

    client = TestClient(app)
    allowed = client.get("/api/core/settings", headers={"Authorization": f"Bearer {view_token}"})
    blocked = client.get("/api/core/settings", headers={"Authorization": f"Bearer {blocked_token}"})

    assert allowed.status_code == 200
    assert blocked.status_code == 403


def test_setting_update_writes_audit_event() -> None:
    edit_token = _token("editor@example.com", ["settings.edit"])
    with TestingSessionLocal() as db:
        db.add(Setting(key="core.timezone", value="UTC"))
        db.commit()

    client = TestClient(app)
    response = client.patch(
        "/api/core/settings/core.timezone",
        headers={"Authorization": f"Bearer {edit_token}"},
        json={"value": "America/Sao_Paulo"},
    )

    assert response.status_code == 200
    assert response.json()["value"] == "America/Sao_Paulo"

    with TestingSessionLocal() as db:
        audit_event = db.scalar(select(AuditEvent).where(AuditEvent.action == "settings.updated"))

    assert audit_event is not None
    assert audit_event.target_id == "core.timezone"


def test_core_health_status_endpoint() -> None:
    token = _token("core@example.com", ["core.view"])
    with TestingSessionLocal() as db:
        db.add_all(
            [
                Module(slug="core", name="Core", version="0.1.0", state="enabled", enabled=True, installed=True, locked=False),
                Module(slug="web", name="Web", version="0.1.0", state="locked", enabled=False, installed=False, locked=True),
                Server(
                    slug="local",
                    name="Local Server",
                    description="Local record",
                    hostname="hostpilot-local",
                    os_name="Ubuntu Server 26.04 LTS",
                    is_local=True,
                ),
                Job(type="mock", module="core", action="mock.dev", status="queued"),
                AuditEvent(
                    action="auth.login.succeeded",
                    target_type="user",
                    target_id="1",
                    outcome="success",
                    metadata_json="{}",
                    created_at=datetime.now(UTC),
                ),
            ]
        )
        db.commit()

    client = TestClient(app)
    response = client.get("/api/core/status", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["core_status"] == "ok"
    assert payload["database_status"] == "ok"
    assert payload["agent_mock_status"] == "ok"
    assert payload["enabled_modules_count"] == 1
    assert payload["locked_modules_count"] == 1
    assert payload["recent_jobs_count"] == 1
    assert payload["recent_audit_events_count"] == 1
    assert payload["local_server"]["name"] == "Local Server"


def test_local_server_update_permissions() -> None:
    edit_token = _token("editor@example.com", ["settings.edit"])
    blocked_token = _token("viewer@example.com", ["core.view"])
    with TestingSessionLocal() as db:
        db.add(
            Server(
                slug="local",
                name="Local Server",
                description="Before",
                hostname="hostpilot-local",
                os_name="Ubuntu Server 26.04 LTS",
                is_local=True,
            )
        )
        db.commit()

    client = TestClient(app)
    blocked = client.patch(
        "/api/core/server/local",
        headers={"Authorization": f"Bearer {blocked_token}"},
        json={"name": "Blocked", "description": "Nope"},
    )
    allowed = client.patch(
        "/api/core/server/local",
        headers={"Authorization": f"Bearer {edit_token}"},
        json={"name": "Primary Host", "description": "Control plane node"},
    )

    assert blocked.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["name"] == "Primary Host"

    with TestingSessionLocal() as db:
        audit_event = db.scalar(select(AuditEvent).where(AuditEvent.action == "server.display.updated"))

    assert audit_event is not None
