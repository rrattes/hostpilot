from collections.abc import Generator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth.security import create_access_token
from app.db.base import Base
from app.db.models import AuditEvent, Job, Permission, Role, User
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


def test_list_audit_events_requires_audit_view_and_filters() -> None:
    token = _token("auditor@example.com", ["audit.view"])
    with TestingSessionLocal() as db:
        db.add_all(
            [
                AuditEvent(
                    actor_user_id=1,
                    action="auth.login.succeeded",
                    target_type="user",
                    target_id="1",
                    outcome="success",
                    metadata_json="{}",
                    created_at=datetime(2026, 6, 5, tzinfo=UTC),
                ),
                AuditEvent(
                    actor_user_id=2,
                    action="auth.login.failed",
                    target_type="user",
                    target_id="2",
                    outcome="failure",
                    metadata_json="{}",
                    created_at=datetime(2026, 6, 6, tzinfo=UTC),
                ),
            ]
        )
        db.commit()

    client = TestClient(app)
    response = client.get(
        "/api/core/audit/events?action=auth.login.failed&status=failure",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["action"] == "auth.login.failed"


def test_audit_event_get_and_permission_denied() -> None:
    allowed_token = _token("audit-viewer@example.com", ["audit.view"])
    blocked_token = _token("viewer@example.com", ["core.view"])
    with TestingSessionLocal() as db:
        event = AuditEvent(
            action="rbac.access_denied",
            target_type="permission",
            target_id="jobs.view",
            outcome="failure",
            metadata_json="{}",
            created_at=datetime.now(UTC),
        )
        db.add(event)
        db.commit()
        event_id = event.id

    client = TestClient(app)
    allowed = client.get(
        f"/api/core/audit/events/{event_id}",
        headers={"Authorization": f"Bearer {allowed_token}"},
    )
    blocked = client.get(
        f"/api/core/audit/events/{event_id}",
        headers={"Authorization": f"Bearer {blocked_token}"},
    )

    assert allowed.status_code == 200
    assert blocked.status_code == 403


def test_list_jobs_requires_jobs_view_and_filters() -> None:
    token = _token("operator@example.com", ["jobs.view"])
    with TestingSessionLocal() as db:
        db.add_all(
            [
                Job(type="mock", module="core", action="mock.dev", status="queued"),
                Job(type="mock", module="core", action="other", status="done"),
            ]
        )
        db.commit()

    client = TestClient(app)
    response = client.get(
        "/api/core/jobs?status=queued&module=core&action=mock.dev",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "queued"


def test_create_mock_job_disabled_by_default() -> None:
    token = _token("jobs@example.com", ["jobs.view"])
    client = TestClient(app)

    response = client.post(
        "/api/core/jobs/mock",
        headers={"Authorization": f"Bearer {token}"},
        json={"module": "core", "action": "mock.dev", "payload": "{\"dryRun\":true}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Development-only mock job creation is disabled."


def test_create_mock_job_writes_audit_event(monkeypatch) -> None:
    monkeypatch.setenv("HOSTPILOT_ENABLE_DEV_ACTIONS", "true")
    token = _token("jobs@example.com", ["jobs.view"])
    client = TestClient(app)

    response = client.post(
        "/api/core/jobs/mock",
        headers={"Authorization": f"Bearer {token}"},
        json={"module": "core", "action": "mock.dev", "payload": "{\"dryRun\":true}"},
    )

    assert response.status_code == 200
    assert response.json()["module"] == "core"
    assert response.json()["action"] == "mock.dev"

    audit_response = client.get(
        "/api/core/audit/events?action=jobs.mock.created",
        headers={"Authorization": f"Bearer {_token('auditor2@example.com', ['audit.view'])}"},
    )

    assert audit_response.status_code == 200
    assert audit_response.json()["total"] == 1


def test_unauthenticated_jobs_blocked() -> None:
    client = TestClient(app)

    response = client.get("/api/core/jobs")

    assert response.status_code == 401
