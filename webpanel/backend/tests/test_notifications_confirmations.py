from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth.security import create_access_token
from app.core.confirmations.models import confirmation_required, is_confirmation_valid
from app.db.base import Base
from app.db.models import AuditEvent, Notification, Permission, Role, User
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


def _token(email: str, permission_slugs: list[str]) -> tuple[str, int]:
    with TestingSessionLocal() as db:
        permissions = [Permission(slug=slug, description="") for slug in permission_slugs]
        role = Role(slug=email.split("@")[0], name="Test Role", permissions=permissions)
        user = User(email=email, display_name="Test User", password_hash="not-used", roles=[role])
        db.add(user)
        db.commit()
        return create_access_token(user.id), user.id


def test_notification_list_permissions() -> None:
    token, user_id = _token("viewer@example.com", ["notifications.view"])
    blocked_token, _ = _token("blocked@example.com", ["core.view"])
    with TestingSessionLocal() as db:
        db.add(Notification(user_id=user_id, title="Test", message="Body", severity="info"))
        db.commit()

    client = TestClient(app)
    allowed = client.get("/api/core/notifications", headers={"Authorization": f"Bearer {token}"})
    blocked = client.get(
        "/api/core/notifications",
        headers={"Authorization": f"Bearer {blocked_token}"},
    )

    assert allowed.status_code == 200
    assert allowed.json()["total"] == 1
    assert blocked.status_code == 403


def test_mark_as_read_and_unread_count() -> None:
    token, user_id = _token(
        "viewer@example.com",
        ["notifications.view", "notifications.manage_own"],
    )
    with TestingSessionLocal() as db:
        notification = Notification(
            user_id=user_id,
            title="Unread",
            message="Body",
            severity="info",
            status="unread",
        )
        db.add(notification)
        db.commit()
        notification_id = notification.id

    client = TestClient(app)
    before = client.get("/api/core/notifications", headers={"Authorization": f"Bearer {token}"})
    marked = client.patch(
        f"/api/core/notifications/{notification_id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    after = client.get("/api/core/notifications", headers={"Authorization": f"Bearer {token}"})

    assert before.json()["unread_count"] == 1
    assert marked.status_code == 200
    assert marked.json()["status"] == "read"
    assert after.json()["unread_count"] == 0
    with TestingSessionLocal() as db:
        audit_event = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "notifications.read")
        )
    assert audit_event is not None
    assert audit_event.target_id == str(notification_id)
    assert audit_event.outcome == "success"


def test_mark_all_as_read() -> None:
    token, user_id = _token(
        "viewer@example.com",
        ["notifications.view", "notifications.manage_own"],
    )
    with TestingSessionLocal() as db:
        db.add_all(
            [
                Notification(user_id=user_id, title="One", message="Body", severity="info"),
                Notification(user_id=user_id, title="Two", message="Body", severity="info"),
            ]
        )
        db.commit()

    client = TestClient(app)
    response = client.patch(
        "/api/core/notifications/read-all",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["unread_count"] == 0
    with TestingSessionLocal() as db:
        audit_event = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "notifications.read_all")
        )
    assert audit_event is not None
    assert audit_event.target_id == "visible"
    assert audit_event.outcome == "success"
    assert '"count": "2"' in audit_event.metadata_json


def test_notification_created_from_mock_agent_job() -> None:
    token, user_id = _token(
        "operator@example.com",
        ["agent.execute_mock", "notifications.view"],
    )
    client = TestClient(app)

    action = client.post(
        "/api/agent/actions/mock.health",
        headers={"Authorization": f"Bearer {token}"},
        json={"payload": {}},
    )
    notifications = client.get(
        "/api/core/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert action.status_code == 200
    assert notifications.status_code == 200
    assert notifications.json()["unread_count"] == 1
    with TestingSessionLocal() as db:
        notification = db.scalar(select(Notification).where(Notification.user_id == user_id))
    assert notification is not None
    assert notification.title == "Mock agent job completed"


def test_confirmation_helper() -> None:
    requirement = confirmation_required(
        action="settings.reset",
        message="Reset settings.",
        risk_level="high",
        required_phrase="RESET",
    )

    assert not is_confirmation_valid(requirement, "reset")
    assert is_confirmation_valid(requirement, "RESET")
